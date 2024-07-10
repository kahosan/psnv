import os
import time
from typing import Literal, TypedDict
from pixivpy3 import AppPixivAPI

from core.db import SQLiteDB
from core.logger import Logger
from lib import utils


class Illust(TypedDict):
    id: int
    title: str
    image_urls: list[str]
    user_id: int


class Pixiv(AppPixivAPI):
    def __init__(self, refresh_token: str | None):
        super().__init__()
        super().auth(refresh_token=refresh_token)

        self.logger = Logger(logger_name="pixiv").get_logger()

    def get_follow_ids(self, user_id: int | str):
        r = self.user_following(user_id)

        follow_ids: list[int] = []

        while True:
            follows: list[dict] = r.get("user_previews")
            for follow in follows:
                id = follow["user"]["id"]
                follow_ids.append(id)

            if not r.get("next_url"):
                break

            qs = self.parse_qs(r.get("next_url"))
            r = self.user_following(**qs)

            time.sleep(1)

        self.logger.info(f"Process {len(follow_ids)} follow")
        return follow_ids

    def collect_illusts(
        self, user_id: int | str, type: Literal["illust"] | Literal["manga"] = "illust"
    ):
        r = self.user_illusts(user_id, type=type)
        collect: list[Illust] = []

        self.logger.info(f"Collecting illusts from user {user_id}")

        while True:
            illusts = r.get("illusts")

            for illust in illusts:
                _illust: Illust = {
                    "id": illust["id"],
                    "title": illust["title"],
                    "user_id": illust["user"]["id"],
                    "image_urls": [],
                }

                if illust.get("meta_single_page"):
                    _illust["image_urls"].append(
                        illust["meta_single_page"]["original_image_url"]
                    )
                elif illust.get("meta_pages"):
                    for page in illust["meta_pages"]:
                        _illust["image_urls"].append(page["image_urls"]["original"])

                collect.append(_illust)

            if not r.get("next_url"):
                break

            qs = self.parse_qs(r.get("next_url"))
            r = self.user_illusts(**qs)

            time.sleep(1)

        return collect

    def process_illusts(self, illusts: list[Illust], root_path: str):
        count = 0
        for illust in illusts:
            path = os.path.join(root_path, str(illust.get("user_id")))
            utils.check_folder_exists(path)

            illust_id = illust.get("id")

            with SQLiteDB() as db:
                c = db.cursor()
                c.execute("SELECT id FROM illust WHERE id = ?", (illust_id,))
                if c.fetchone():
                    continue

                illust_title = illust.get("title")
                illust_user_id = illust.get("user_id")

                try:
                    self.logger.info(f"Processing illust {illust_id}")
                    self.download_illust(illust=illust, root_path=path)
                    c.execute(
                        "INSERT INTO illust (id, title, user_id) VALUES (?, ?, ?)",
                        (illust_id, illust_title, illust_user_id),
                    )
                    db.commit()
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to download {illust_id}: {e}")
                    continue

        self.logger.info(
            f"Success add {count} illusts" if count > 0 else "No new illusts"
        )

    def download_illust(self, illust: Illust, root_path: str):
        import requests

        id = illust.get("id")
        title = utils.normalize_name(illust.get("title"))
        urls = illust.get("image_urls")

        if len(urls) > 1:
            root_path = os.path.join(root_path, f"{title}_{str(id)}")
            utils.check_folder_exists(root_path)

        for url in urls:
            file_name = f"{title}_{url.split("/").pop()}"
            path = os.path.join(root_path, file_name)
            if os.path.exists(path):
                continue

            with requests.get(
                url, headers={"Referer": "https://app-api.pixiv.net/"}, stream=True
            ) as r:
                r.raise_for_status()
                with open(path, "wb") as file:
                    for chunk in r.iter_content(chunk_size=8192):
                        file.write(chunk)
