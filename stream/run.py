from datetime import datetime as dt
from urllib.parse import unquote
from random import randrange
import requests
import inspect
import json
import time
import re

from playwright.sync_api import sync_playwright, Response, Playwright
import pytz

from .logger import get_logger
from .models import PostData, UserData, Entities, AccountMention
from .producer import produce_to_kafka


date = dt.now().strftime('%Y%m%d')
timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')
logger = get_logger(log_name="Deckster")
LOCAL_TIME = pytz.timezone('Asia/Riyadh')


def random_sleep(): time.sleep(randrange(2, 6))


def convert_datetime(created_at: str) -> str:
    utc_time = dt.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    local_dt = utc_time.replace(tzinfo=pytz.utc).astimezone(LOCAL_TIME)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')


def parse_tweets(posts: list, rule: str, file_name: str = './data/parsed_tweets.jsonl'):
    with open(file_name, 'a') as f:
        for post in posts:
            if str(post.get('entryId', '')).startswith('tweet'):
                try:
                    # Extract relevant parts of the tweet data
                    result = post.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                    post_content = result.get('tweet', {}) if result.get('__typename') == 'TweetWithVisibilityResults' else result
                    legacy_data = post_content.get('legacy', {})

                    # User details
                    user_content = post_content.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {})
                    user_data = UserData(
                        user_id=post_content.get('core', {}).get('user_results', {}).get('result', {}).get('rest_id', ''),
                        username=user_content.get('name', ''),
                        screen_name=user_content.get('screen_name', ''),
                        followers=user_content.get('followers_count', 0),
                        verified=user_content.get('verified', False),
                        verified_type='none' if not user_content.get('verified') else 'blue',
                        posts_count=user_content.get('statuses_count', 0),
                        account_mentions=[
                            AccountMention(
                                screen_name=mention.get('screen_name', ''),
                                name=mention.get('name', ''),
                                id_str=mention.get('id_str', '')
                            ) for mention in legacy_data.get('entities', {}).get('user_mentions', [])
                        ]
                    )

                    # Entities: hashtags, URLs, media
                    entities = Entities(
                        hashtags=[hashtag.get('text') for hashtag in legacy_data.get('entities', {}).get('hashtags', [])],
                        urls=[url.get('expanded_url') for url in legacy_data.get('entities', {}).get('urls', [])],
                        media_urls=[media.get('media_url_https') for media in legacy_data.get('extended_entities', {}).get('media', [])]
                    )

                    # Post type logic
                    post_type = (
                        'quoted' if legacy_data.get('is_quote_status', False)
                        else 'reply' if legacy_data.get('in_reply_to_status_id_str')
                        else 'retweet' if post_content.get('retweeted_status_result')
                        else 'post'
                    )

                    # Create a PostData model
                    post_data = PostData(
                        posted_date_utc=legacy_data.get('created_at'),
                        post_id=legacy_data.get('id_str'),
                        text=legacy_data.get('full_text', ''),
                        local_posted=convert_datetime(legacy_data.get('created_at')),
                        post_type=post_type,
                        language=legacy_data.get('lang', 'en'),
                        likes=legacy_data.get('favorite_count', 0),
                        retweets=legacy_data.get('retweet_count', 0),
                        quotes=legacy_data.get('quote_count', 0),
                        conversation_id=legacy_data.get('conversation_id_str'),
                        user_data=user_data,
                        entities=entities,
                        geo_location=post_content.get('geo', {}).get('coordinates') if 'geo' in post_content else None,
                        rule=rule
                    )

                    # f.write(json.dumps(post_data.model_dump()) + '\n')
                    produce_to_kafka('posts', post_data.model_dump(), post_data.language)
                except Exception as e:
                    print(post_data.model_dump())
                    logger.error(f"{e}", exc_info=True)


def parse_json(response: Response):
    if 'SearchTimeline' in response.url:
        try:
            query = json.loads(re.findall("{.+}(?=&)", unquote(response.request.url))[0])['rawQuery']
            instructions = response.json()['data']['search_by_raw_query']['search_timeline']['timeline']['instructions']
            for instruction in instructions:
                if instruction.get('type', '') == 'TimelineAddEntries':
                    logger.debug(f"{len(instruction['entries'])} posts found for query {query}")
                    parse_tweets(instruction['entries'], query)
        except Exception as e:
            logger.warning(f"Warning @{inspect.currentframe().f_code.co_name} caller={inspect.currentframe().f_back.f_code.co_name} error={e}")
            pass


def parse_headers(request):
    try:
        if 'GetUserClaims' in request.url:
            headers = request.all_headers()
            key_list = [':authority', ':method', ':path', ':scheme']
            [headers.pop(key) for key in key_list]
            with open('./stream/resources/headers.json', mode='w', encoding='utf-8') as headers_file:
                json.dump(headers, headers_file)
    except Exception as e:
        logger.error(f"Error @{inspect.currentframe().f_code.co_name} caller={inspect.currentframe().f_back.f_code.co_name} error={e}", exc_info=True)
        pass


def load_deck(playwright: Playwright, username, password, email):
    chromium = playwright.chromium
    browser = chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()

    page.on("request", lambda request: parse_headers(request))
    page.on("response", lambda response: parse_json(response))
    page.set_default_timeout(100000000)
    page.goto("https://pro.twitter.com")
    page.wait_for_load_state("networkidle")
    login_button = page.locator("//*[@id='react-root']/div/div/main/div/div[1]/a")
    login_button.click()
    logger.info(f"Attempting login with user {username}")
    random_sleep()
    page.click("//input[@name='text']")
    random_sleep()
    page.locator(selector="//input[@name='text']").type(username, delay=30)
    random_sleep()
    page.keyboard.press("Enter")
    random_sleep()
    if 'email' in page.locator('//h1[@role="heading"]').inner_text():
        if email == 'example@email.com':
            logger.warning(f"Stopping run. Generic email entered {email}")
            page.close()
            browser.close()
            return {}
        email_field = page.locator('//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]/div/input')
        email_field.click()
        email_field.type(email, delay=30)
        random_sleep()
        page.keyboard.press("Enter")
    random_sleep()
    page.locator(selector="//input[@name='password']").type(password, delay=30)
    random_sleep()
    page.keyboard.press("Enter")
    random_sleep()
    logger.info(f"User login successful")

    while True:
        time.sleep(10)
        page.mouse.wheel(0, 0)
        status = requests.get("http://dexter-columns:5000/status").json()['status']
        if status == 'reload':
            res = requests.post("http://dexter-columns:5000/reload", json={"page": "idle"})
            logger.info(f"{res.json().get('message', {})}, reloading page") if res.status_code == 200 else logger.error(f"{res.text}")
            page.close()
            page = context.new_page()
            page.on("response", lambda response: parse_json(response))
            page.wait_for_load_state('load')
            page.goto("https://pro.twitter.com")
            continue

        if dt.utcnow().strftime('%H:%M:%S') == '00:00:00':
            logger.info("Reloading page")
            page.goto("https://pro.twitter.com")


def get_stream(user, password, email):
    logger.info(f"Run started...")
    with sync_playwright() as pw:
        load_deck(pw, user, password, email)
