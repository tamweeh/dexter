from datetime import datetime as dt
from urllib.parse import unquote
from random import randrange
import requests
import inspect
import json
import time
import re

from playwright.sync_api import sync_playwright, Response, Playwright, Page, Request
from dotenv import load_dotenv
import pytz

from .utils import get_timezone, redis_connection, x_api, dexter_columns_host
from .logger import get_logger
from .models import PostData, UserData, Entities, AccountMention
from .producer import send_message

load_dotenv()
# date = dt.now().strftime('%Y%m%d')
# timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')
logger = get_logger(log_name="Deckster")
LOCAL_TIME = pytz.timezone(get_timezone())
redis_client = redis_connection()

def _random_sleep(): time.sleep(randrange(2, 6))


def _convert_datetime(created_at: str) -> tuple[str, str]:
    utc_time = dt.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    local_dt = utc_time.replace(tzinfo=pytz.utc).astimezone(LOCAL_TIME)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S'), utc_time.strftime('%Y-%m-%d %H:%M:%S')


def _parse_posts(posts: list, rule: str, file_name: str = './data/parsed_tweets.jsonl'):
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
                    username=user_content.get('screen_name', ''),
                    display_name=user_content.get('name', ''),
                    followers=user_content.get('followers_count', 0),
                    verified=user_content.get('verified', False),
                    verified_type='none' if not user_content.get('verified') else 'blue',
                    posts_count=user_content.get('statuses_count', 0),
                    account_mentions=[
                        AccountMention(
                            username=mention.get('screen_name', ''),
                            display_name=mention.get('name', ''),
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
                local_time, utc = _convert_datetime(legacy_data.get('created_at'))

                # Create a PostData model
                post_data = PostData(
                    posted_date_utc=utc,
                    post_id=legacy_data.get('id_str'),
                    text=legacy_data.get('full_text', ''),
                    local_posted=local_time,
                    post_type=post_type,
                    language=legacy_data.get('lang', 'en'),
                    likes=legacy_data.get('favorite_count', 0),
                    retweets=legacy_data.get('retweet_count', 0),
                    quotes=legacy_data.get('quote_count', 0),
                    conversation_id=legacy_data.get('conversation_id_str'),
                    user_data=user_data,
                    entities=entities,
                    rule=rule,
                    collection_time=dt.now().strftime('%Y-%m-%d_%H-%M-%S')
                )

                # f.write(json.dumps(post_data.model_dump()) + '\n')
                send_message(topic='posts', key=post_data.language, value=post_data.model_dump())
            except Exception as e:
                print(post)
                logger.error(f"{e}", exc_info=True)


def _parse_json(response: Response):
    if 'SearchTimeline' in response.url:
        try:
            query = json.loads(re.findall("{.+}(?=&)", unquote(response.request.url))[0])['rawQuery']
            instructions = response.json()['data']['search_by_raw_query']['search_timeline']['timeline']['instructions']
            for instruction in instructions:
                if instruction.get('type', '') == 'TimelineAddEntries':
                    data = instruction['entries']
                    logger.debug(f"{len(data)} posts found for query={query}")
                    # logger.debug(f"{len(data)} posts found", extra={"query": query})
                    _parse_posts(data, query)
        except Exception as e:
            logger.warning(f"Warning @{inspect.currentframe().f_code.co_name} caller={inspect.currentframe().f_back.f_code.co_name} error={e}")
            pass


def _parse_headers(request: Request, user):
    if 'GetUserClaims' in request.url:
        try:
            headers = request.all_headers()
            key_list = [':authority', ':method', ':path', ':scheme']
            [headers.pop(key) for key in key_list]
            redis_client.hset(f'user:{user}', mapping=headers)
            logger.info("Saved user headers")
        except Exception as e:
            logger.warning("Could not get user headers")
            logger.error(f"Error @{inspect.currentframe().f_code.co_name} caller={inspect.currentframe().f_back.f_code.co_name} error={e}", exc_info=True)
            pass

def _login(login_page: Page, username: str, passcode: str, email: str) -> bool:
    login_button = login_page.locator("//*[@id='react-root']/div/div/main/div/div[1]/a")
    login_button.click()
    logger.info(f"Attempting login with user {username}")
    _random_sleep()
    login_page.locator(selector="//input[@name='text']").click()
    _random_sleep()
    login_page.locator(selector="//input[@name='text']").type(username, delay=30)
    _random_sleep()
    login_page.keyboard.press("Enter")
    _random_sleep()
    if 'email' in login_page.locator('//h1[@role="heading"]').inner_text():
        email_field = login_page.locator('//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]/div/input')
        email_field.click()
        email_field.type(email, delay=30)
        _random_sleep()
        login_page.keyboard.press("Enter")
    _random_sleep()
    login_page.locator(selector="//input[@name='password']").type(passcode, delay=30)
    _random_sleep()
    login_page.keyboard.press("Enter")
    _random_sleep()
    while login_page.url == f'{x_api()}/i/flow/login':
        logger.debug("Waiting for login...")
        login_page.wait_for_load_state("load")
    else:
        logger.info(f"User login successful")
        return True


def _load_deck(playwright: Playwright, username, password, email):
    chromium = playwright.chromium
    browser = chromium.launch(headless=True, args=["--start-maximized", "--disable-gpu", "--disable-infobars", "--no-sandbox"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()

    page.on("request", lambda request: _parse_headers(request, username))
    page.on("response", lambda response: _parse_json(response))
    page.set_default_timeout(100000000)
    page.goto(x_api())
    page.wait_for_load_state("networkidle")

    if not _login(page, username, password, email):
        page.close()
        browser.close()
        raise logger.critical('Login unsuccessful')

    while True:
        time.sleep(5)
        page.mouse.wheel(0, 0)
        try:
            status = requests.get(f"{dexter_columns_host()}/status").json()['status']
            if status == 'reload':
                res = requests.post(f"{dexter_columns_host()}/reload", json={"page": "running"})
                logger.info(f"{res.json().get('message', {})} - Reloading page") if res.status_code == 200 else logger.error(f"{res.text}")
                page.close()
                page = context.new_page()
                page.on("response", lambda response: _parse_json(response))
                page.wait_for_load_state('load')
                page.goto(x_api())
                continue
        except Exception as e:
            logger.error(f"{e}")
            continue

        if dt.utcnow().strftime('%H:%M:%S') == '00:00:00':
            logger.info("New day - Reloading page")
            page.goto(x_api())


def get_stream(user, password, email):
    logger.info(f"Welcome to Dexter")
    with sync_playwright() as pw:
        _load_deck(pw, user, password, email)
