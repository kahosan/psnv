import json
from typing import TypedDict


class BaseType(TypedDict):
    novel: bool
    illust: bool
    manga: bool


class BaseFields(TypedDict):
    enabled: bool
    save_path: str
    type: BaseType


class Config(TypedDict):
    refresh_token: str
    telegram_bot_token: str
    follow: BaseFields
    favorite: BaseFields
    ranking: BaseFields


def load_config() -> Config:
    with open("config.json", "r") as f:
        return json.load(f)
