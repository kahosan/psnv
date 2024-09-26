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


class NovelSeries(Novel):
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
            follows = r.get("user_previews")

            if not follows:
                self.logger.error("Failed to get follows, user_previews is none")
                qs = self.parse_qs(next_url)
                time.sleep(1)
                continue

            for follow in follows:
                id = follow.get("user").get("id")
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
                    "id": illust.get("id"),
                    "title": illust.get("title"),
                    "user_id": illust.get("user").get("id"),
                    "image_urls": [],
                }

                if illust.get("meta_single_page"):
                    _illust.get("image_urls").append(
                        illust.get("meta_single_page").get("original_image_url")
                    )
                elif illust.get("meta_pages"):
                    for page in illust.get("meta_pages"):
                        _illust.get("image_urls").append(
                            page.get("image_urls").get("original")
                        )

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
        collect: tuple[list[Novel], list[NovelSeries]] = ([], [])

        self.logger.info(f"Collecting novels from user {user_id}")

        series_set = set()
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
                if novel.get("is_mypixiv_only"):
                    continue

                series_id = novel.get("series").get("id")
                if series_id and (series_id not in series_set):
                    series_set.add(series_id)
                    collect[1].append(
                        {
                            "id": series_id,
                            "title": novel.get("series").get("title"),
                            "user_id": novel.get("user").get("id"),
                            "cover_url": novel.get("image_urls").get("large"),
                        }
                    )
                elif not series_id:
                    collect[0].append(
                        {
                            "id": novel.get("id"),
                            "title": novel.get("title"),
                            "user_id": novel.get("user").get("id"),
                        }
                    )

            qs = self.parse_qs(next_url)
            time.sleep(1)

        # 0 = novel, 1 = series
        return collect

    def process_novels(self, novels: list[Novel], root_path: str):
        root_path = os.path.join(root_path, "novels")

        for novel in novels:
            self.logger.info(
                f"Processing novel {novel.get("id")}, {novel.get("title")}"
            )

            path = os.path.join(root_path, str(novel.get("user_id")))
            utils.check_folder_exists(path)

            novel_id = novel.get("id")

            with SQLiteDB() as db:
                c = db.cursor()
                c.execute("SELECT id FROM novel WHERE id = ?", (novel_id,))
                if c.fetchone():
                    continue

                novel_title = novel.get("title")
                user_id = novel.get("user_id")

                try:
                    self.download_novel(novel=novel, root_path=path)
                    c.execute(
                        "INSERT INTO novel (id, title, user_id) VALUES (?, ?, ?)",
                        (
                            novel_id,
                            novel_title,
                            user_id,
                        ),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to download {novel_id}: {e}")
                    continue

    def process_novels_series(self, series_list: list[NovelSeries], root_path: str):
        root_path = os.path.join(root_path, "novels")

        for series in series_list:
            path = os.path.join(root_path, str(series.get("user_id")))
            utils.check_folder_exists(path)

            qs: Qs = {"series_id": series.get("id")}
            no = 0
            self.logger.info(
                f"Processing novel series {series.get("id")}, {series.get('title')}"
            )
            while qs:
                r = self.novel_series(**qs)
                next_url = r.get("next_url")
                novels = r.get("novels")

                if novels is None:
                    self.logger.error(
                        f"Failed to process series {series}, novels is none"
                    )
                    qs = self.parse_qs(next_url)
                    time.sleep(1)
                    continue

                for novel in novels:
                    if novel.get("is_mypixiv_only"):
                        continue

                    novel_id = novel.get("id")
                    novel_title = novel.get("title")

                    no += 1

                    _novel: Novel = {
                        "id": novel_id,
                        "title": novel_title,
                        "user_id": series.get("user_id"),
                    }

                    with SQLiteDB() as db:
                        c = db.cursor()
                        c.execute("SELECT id FROM novel WHERE id = ?", (novel_id,))
                        if c.fetchone():
                            continue

                        try:
                            self.download_novel(
                                novel=_novel,
                                root_path=path,
                                novel_no=no,
                                series=series,
                            )
                            c.execute(
                                "INSERT INTO novel (id, title, user_id, series_id, series_title, cover_url) VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    novel_id,
                                    novel_title,
                                    series.get("user_id"),
                                    series.get("id"),
                                    series.get("title"),
                                    series.get("cover_url"),
                                ),
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to download {series.get("id")}, novel no {no}: {e}"
                            )
                            continue

                qs = self.parse_qs(next_url)
                time.sleep(1)

    def download_novel(
        self,
        novel: Novel,
        root_path: str,
        novel_no: int | None = None,
        series: NovelSeries | None = None,
    ):
        id = novel.get("id")
        title = utils.normalize_name(novel.get("title"))

        cover_url, series_id, series_title = (
            (None, None, None)
            if not series
            else (
                series.get("cover_url"),
                series.get("id"),
                series.get("title"),
            )
        )

        if series_id and series_title and novel_no and cover_url:
            title = f"{novel_no}. {title}"
            series_title = utils.normalize_name(series_title)
            root_path = os.path.join(root_path, f"{series_title}_{str(series_id)}")
            utils.check_folder_exists(root_path)

            utils.download_file(
                os.path.join(root_path, f"{series_title}.jpg"),
                cover_url.replace("c/240x480_80", ""),
            )

        novel_text = self.novel_text(id).get("text")

        max_filename_length = 255
        if len(title) > max_filename_length:
            title = title[:max_filename_length]

        with open(os.path.join(root_path, f"{title}.txt"), "w", encoding="utf-8") as f:
            for line in novel_text.strip().split("\n"):
                f.write(line.strip() + "\n")
