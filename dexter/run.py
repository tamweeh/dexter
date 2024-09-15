from datetime import datetime as dt
from time import sleep
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

from .parser import _parse_posts
from .utils import get_timezone, redis_connection, x_api, dexter_columns_host
from .logger import get_logger
from .producer import send_message

load_dotenv()

logger = get_logger(log_name=__name__.split('.')[-1])
LOCAL_TIME = pytz.timezone(get_timezone())
redis_client = redis_connection()

def _random_sleep(): time.sleep(randrange(2, 6))


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
                    for post in _parse_posts(data, query):
                        send_message(topic='posts', key=post.post_type, value=post.model_dump())
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
        sleep(0.5)
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
