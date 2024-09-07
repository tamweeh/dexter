import json

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from urllib.parse import unquote
import re
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from stream import deck_columns as cols

app = FastAPI()
templates = Jinja2Templates(directory='./templates')


# Pydantic models for request validation
class RemoveColumnRequest(BaseModel):
    column_id: str


class UpdateColumnRequest(BaseModel):
    query: str
    column_id: str


class ReloadPageRequest(BaseModel):
    page: str


page_status = "idle"


@app.get("/")
async def running(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/columns")
async def get_columns():
    exiting_columns = cols.get_deck_info()
    cols_info = []
    deck_info = {"deck_id": exiting_columns['data']['viewer_v2']['decks'][0]['rest_id'], "columns": cols_info}
    for col in exiting_columns['data']['viewer_v2']['decks'][0]['deck_columns_v2']:
        try:
            col_detail = {
                'column_id': col['rest_id'],
                'query': "",
                'creator': {
                    'username': col['creator_ref_results']['result']['legacy']['screen_name'],
                    'user_id': col['creator_ref_results']['result']['rest_id']
                }
            }
        except Exception:
            return JSONResponse(deck_info)
        try:
            query = col['pathname']
            query_cleaned = re.findall('(?<=\?q=).+?(?=&.*?=)', query)
            col_detail['query'] = unquote(query_cleaned[0])
        except Exception as e:
            col_detail['query'] = "no query found, empty column"
            col_detail['exception'] = f"{e}"

        cols_info.append(col_detail)
    deck_info.update({"columns": cols_info})
    return JSONResponse(deck_info)


@app.get("/columns_raw")
async def get_columns_raw():
    return JSONResponse(cols.get_deck_info())


@app.post("/add_column")
async def add_column():
    response = await get_columns()
    response_json = json.loads(response.body.decode('utf-8'))
    columns = response_json['columns']
    deck_id = response_json['deck_id']
    try:
        column_list = [c['column_id'] for c in columns]
    except Exception:
        column_list = []
    add_status = cols.add_column(column_list, deck_id)
    return {"action": {"add_column": "request new column"}, "API_response": add_status}


@app.post("/update_column")
async def update_column(request: UpdateColumnRequest):
    response = await get_columns()
    response_json = json.loads(response.body.decode('utf-8'))
    columns = response_json['columns']
    deck_id = response_json['deck_id']
    try:
        column_list = [c['column_id'] for c in columns]
    except Exception:
        column_list = []

    col_id, q = request.column_id, request.query
    update_status = cols.update_column(col_id, q, column_list, deck_id)
    global page_status
    page_status = 'reload' if page_status == 'running' else 'idle'
    return {"action": {"update_column": f"{col_id}", "query": f"{q}"},
            "API_response": update_status,
            "page_status": page_status}


@app.post("/remove_column")
async def remove_column(request: RemoveColumnRequest):
    response = await get_columns()
    response_json = json.loads(response.body.decode('utf-8'))
    columns = response_json['columns']
    deck_id = response_json['deck_id']
    try:
        column_list = [c['column_id'] for c in columns]
    except Exception:
        column_list = []

    content = request.column_id
    remove_status = cols.remove_column(content, column_list, deck_id)
    global page_status
    page_status = 'reload' if page_status == 'running' else 'idle'
    return {"action": {"remove_column": f"{content}"}, "API_response": remove_status}


@app.post("/reload")
async def reload_page(request: ReloadPageRequest):
    global page_status
    if request.page == 'reload':
        page_status = "reload"
    else:
        page_status = "running"
    return {"message": "Column(s) updated"}


@app.get("/status")
async def reload_status():
    return {"status": page_status}
