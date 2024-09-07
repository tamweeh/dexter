from urllib.parse import quote
import requests
import json

from .logger import get_logger

logger = get_logger(log_name='deck_columns')

with open('stream/resources/headers.json', mode='r', encoding='utf-8') as req_headers:
    headers = json.loads(req_headers.read())


def get_deck_info() -> dict:
    res = requests.get('https://pro.twitter.com/i/api/graphql/4t9h5GMFYewreBfk9TUKhw/ViewerAccountSync?variables=%7B%7D', headers=headers)
    return res.json() if res.status_code == 200 else {}


def add_column(col_list: list, deck_id: str) -> dict or str:
    new_list = col_list
    if len(col_list) >= 5:
        return {"detail": "Cannot add new column. Max column count reached"}
    payload = {"variables": {"deckId": deck_id, "hideHeader": True, "latest": True, "mediaPreview": "Cropped", "pathname": "/i/columns/picker?urtUrl=",
                             "width": "Medium"}, "queryId": "O4iIdjZUiZpm0KBSiftNGQ"}
    res = requests.post('https://pro.twitter.com/i/api/graphql/O4iIdjZUiZpm0KBSiftNGQ/CreateColumn', headers=headers, json=payload)
    new_list.extend(res.json()['data']['deckcolumn_insert']['rest_id'])
    reorder_columns(new_list)
    return res.json()['data'] if res.status_code == 200 else {}


def reorder_columns(col_list: list):
    payload = {"variables": {"columnOrder": col_list, "deckId": "1632740447926857728"}, "queryId": "JJpn5RKFDbYXC957QragBQ"}
    res = requests.post('https://pro.twitter.com/i/api/graphql/JJpn5RKFDbYXC957QragBQ/ReorderColumns', headers=headers, json=payload)
    logger.info(f'REORDER STATUS: {res.status_code}') if res.status_code == 200 else logger.error(f'REORDER STATUS: {res.status_code}')


def update_column(col_id: str, query: str, col_list: list, deck_id: str) -> dict or str:
    q = quote(query)
    if col_id not in col_list:
        return {"detail": "column ID does not exist"}

    payload = {"variables": {"columnId": col_id, "deckId": deck_id, "drawerSelectedTab": "Search", "hideHeader": True, "latest": True,
                             "pathname": f"/search?q={q}&src=advanced_search_page&f=live", "width": "Narrow"}, "queryId": "suRGd49L2EZ0nuuU4he4aw"}

    res = requests.post('https://pro.twitter.com/i/api/graphql/suRGd49L2EZ0nuuU4he4aw/UpdateColumn', headers=headers, json=payload)
    return res.json()['data']


def remove_column(col_id: str, col_list: list, deck_id: str) -> dict or str:
    new_list = col_list
    if col_id not in col_list:
        return "column ID does not exist"
    payload = {"variables": {"columnId": col_id, "deckId": deck_id}, "queryId": "lfB7GP4w9oCpx5F_BxwRkw"}
    res = requests.post('https://pro.twitter.com/i/api/graphql/lfB7GP4w9oCpx5F_BxwRkw/RemoveColumn', headers=headers, json=payload)
    new_list.remove(col_id)
    reorder_columns(new_list)
    return res.json()['data'] if res.status_code == 200 else {}
