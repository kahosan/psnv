import os
import time
from typing import Any, TypedDict
from pixivpy3 import AppPixivAPI

from core.db import SQLiteDB
from core.logger import Logger
from lib import utils

type Qs = dict[str, Any] | None


class Illust(TypedDict):
    id: int
    title: str
    image_urls: list[str]
    user_id: int


class Novel(TypedDict):
    id: int
    title: str
    user_id: int
    series_id: int | None
    series_title: str | None
    cover_url: str


class Pixiv(AppPixivAPI):
    def __init__(self, refresh_token: str | None):
        super().__init__()
        super().auth(refresh_token=refresh_token)

        self.logger = Logger(logger_name="pixiv").get_logger()

    def get_follow_ids(self, user_id: int | str):
        follow_ids: list[int] = []

        qs: Qs = {"user_id": user_id}
        while qs:
            r = self.user_following(**qs)
            next_url = r.get("next_url")
            follows: list[dict] = r.get("user_previews")

            if not follows:
                self.logger.error("Failed to get follows, user_previews is none")
                qs = self.parse_qs(next_url)
                time.sleep(1)
                continue

            for follow in follows:
                id = follow["user"]["id"]
                follow_ids.append(id)

            qs = self.parse_qs(next_url)
            time.sleep(1)

        self.logger.info(f"Process {len(follow_ids)} follow")
        return follow_ids

    def collect_illusts(self, user_id: int | str):
        collect: list[Illust] = []

        self.logger.info(f"Collecting illusts from user {user_id}")

        qs: Qs = {"user_id": user_id, "type": "illust"}
        while qs:
            r = self.user_illusts(**qs)
            next_url = r.get("next_url")
            illusts = r.get("illusts")

            if illusts is None:
                self.logger.error(
                    f"Failed to collect illusts from user {user_id}, illusts is none"
                )
                qs = self.parse_qs(next_url)
                time.sleep(1)
                continue

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

            qs = self.parse_qs(next_url)
            time.sleep(1)

        return collect

    def process_illusts(self, illusts: list[Illust], root_path: str):
        root_path = os.path.join(root_path, "illusts")

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
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to download {illust_id}: {e}")
                    continue

        self.logger.info(
            f"Success add {count} illusts" if count > 0 else "No new illusts"
        )

    def download_illust(self, illust: Illust, root_path: str):
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

            utils.download_file(path, url)

    def collect_novels(self, user_id: int | str):
        collect: list[Novel] = []

        self.logger.info(f"Collecting novels from user {user_id}")

        qs: Qs = {"user_id": user_id}
        while qs:
            r = self.user_novels(**qs)
            next_url = r.get("next_url")
            novels = r.get("novels")

            if novels is None:
                self.logger.error(
                    f"Failed to collect novels from user {user_id}, novels is none"
                )
                qs = self.parse_qs(next_url)
                time.sleep(1)
                continue

            for novel in novels:
                _novel: Novel = {
                    "id": novel["id"],
                    "title": novel["title"],
                    "user_id": novel["user"]["id"],
                    "series_id": novel.get("series").get("id"),
                    "series_title": novel.get("series").get("title"),
                    "cover_url": novel.get("image_urls").get("large"),
                }
                collect.append(_novel)

            qs = self.parse_qs(next_url)
            time.sleep(1)

        return collect

    def process_novels(self, novels: list[Novel], root_path: str):
        root_path = os.path.join(root_path, "novels")

        count = 0
        for novel in novels:
            path = os.path.join(root_path, str(novel.get("user_id")))
            utils.check_folder_exists(path)

            novel_id = novel.get("id")

            with SQLiteDB() as db:
                c = db.cursor()
                c.execute("SELECT id FROM novel WHERE id = ?", (novel_id,))
                if c.fetchone():
                    continue

                novel_title = novel.get("title")
                novel_user_id = novel.get("user_id")

                try:
                    self.logger.info(f"Processing novel {novel_id}")
                    self.download_novel(novel=novel, root_path=path)
                    c.execute(
                        "INSERT INTO novel (id, title, user_id, series_id, series_title, cover_url) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            novel_id,
                            novel_title,
                            novel_user_id,
                            novel.get("series_id"),
                            novel.get("series_title"),
                            novel.get("cover_url"),
                        ),
                    )
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to download {novel_id}: {e}")
                    continue

        self.logger.info(
            f"Success add {count} novels" if count > 0 else "No new novels"
        )

    def download_novel(self, novel: Novel, root_path: str):
        id = novel.get("id")
        title = utils.normalize_name(novel.get("title"))
        cover_url = novel.get("cover_url")

        series_id = novel.get("series_id")
        series_title = novel.get("series_title")

        if series_id and series_title:
            series_title = utils.normalize_name(series_title)
            root_path = os.path.join(root_path, f"{series_title}_{str(series_id)}")
            utils.check_folder_exists(root_path)

            utils.download_file(
                os.path.join(root_path, f"{series_title}.jpg"),
                cover_url.replace("c/240x480_80", ""),
            )

        novel_text = self.novel_text(id).get("text")

        with open(os.path.join(root_path, f"{title}.txt"), "w", encoding="utf-8") as f:
            for line in novel_text.strip().split("\n"):
                f.write(line.strip() + "\n")
