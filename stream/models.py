from pydantic import BaseModel, Field
from typing import List, Optional
import json
from datetime import datetime


class AccountMention(BaseModel):
    screen_name: str = Field(default="")
    name: str = Field(default="")
    id_str: Optional[str] = None


class Entities(BaseModel):
    hashtags: List[str] = []
    urls: List[str] = []
    media_urls: List[str] = []


class UserData(BaseModel):
    user_id: Optional[str]
    username: str = ""
    screen_name: str = ""
    followers: int = 0
    verified: bool = False
    verified_type: str = "none"
    posts_count: int = 0
    account_mentions: List[AccountMention] = []


class PostData(BaseModel):
    post_id: str
    text: str = ""
    posted_date_utc: str
    local_posted: str
    post_type: str
    language: str
    likes: int
    retweets: int
    quotes: int
    conversation_id: Optional[str]
    user_data: UserData
    entities: Entities
    geo_location: Optional[List[float]] = None
    rule: str
