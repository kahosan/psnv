import json
from pathlib import Path
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
    config_path = Path("config.json")
    with config_path.open("r") as f:
        return json.load(f)
