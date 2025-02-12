from pydantic import BaseModel, Field
from typing import List, Optional


class AccountMention(BaseModel):
    username: str = Field(default="")
    display_name: str = Field(default="")
    id_str: Optional[str] = None


class Entities(BaseModel):
    hashtags: List[str] = []
    urls: List[str] = []
    media_urls: List[str] = []


class UserData(BaseModel):
    user_id: Optional[str]
    username: str = ""
    display_name: str = ""
    followers: int = 0
    verified: bool = False
    verified_type: str = "none"
    posts_count: int = 0
    account_mentions: List[AccountMention] = []


class PostData(BaseModel):
    posted_date_utc: str
    post_id: str
    text: str = ""
    local_posted: str
    post_type: str
    language: str
    likes: int
    retweets: int
    quotes: int
    conversation_id: Optional[str]
    user_data: UserData
    entities: Entities
    rule: str
    data_provider:  str
    collection_time: str