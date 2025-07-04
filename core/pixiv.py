import time
from pathlib import Path
from typing import Any, TypedDict

from pixivpy3 import AppPixivAPI

from core.db import SQLiteDB
from core.logger import Logger
from lib import utils

type Qs = dict[str, Any] | None


class Illust(TypedDict):
    id: int
    title: str
    create_date: str
    image_urls: list[str]
    user_id: int


class UserIllust(TypedDict):
    user_id: int
    user_name: str
    illusts: list[Illust]


class Novel(TypedDict):
    id: int
    title: str
    user_id: int
    user_name: str


class NovelSeries(Novel):
    cover_url: str


class UserFollow(TypedDict):
    follow_id: int
    follow_name: str


class Pixiv(AppPixivAPI):
    def __init__(self, refresh_token: str | None):
        super().__init__()
        super().auth(refresh_token=refresh_token)

        self.logger = Logger(logger_name="pixiv").get_logger()

    def get_user_follows(self, user_id: int | str):
        user_follow_collect: list[UserFollow] = []

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
                name = follow.get("user").get("name")
                user_follow_collect.append({"follow_id": id, "follow_name": name})

            qs = self.parse_qs(next_url)
            time.sleep(1)

        self.logger.info(f"Process {len(user_follow_collect)} follow")
        return user_follow_collect

    def collect_illusts(self, user_id: int | str, user_name: str) -> UserIllust:
        illust_collect: list[Illust] = []

        self.logger.info(f"Collecting illusts from user {user_name}_{user_id}")

        qs: Qs = {"user_id": user_id, "type": "illust"}
        while qs:
            r = self.user_illusts(**qs)
            next_url = r.get("next_url")
            illusts = r.get("illusts")

            if illusts is None:
                self.logger.error(f"Failed to collect illusts from user {user_id}, illusts is none")
                qs = self.parse_qs(next_url)
                time.sleep(1)
                continue

            for illust in illusts:
                _illust: Illust = {
                    "id": illust.get("id"),
                    "title": illust.get("title"),
                    "user_id": illust.get("user").get("id"),
                    "create_date": illust.get("create_date"),
                    "image_urls": [],
                }

                if illust.get("meta_single_page"):
                    _illust.get("image_urls").append(illust.get("meta_single_page").get("original_image_url"))
                elif illust.get("meta_pages"):
                    for page in illust.get("meta_pages"):
                        _illust.get("image_urls").append(page.get("image_urls").get("original"))

                illust_collect.append(_illust)

            qs = self.parse_qs(next_url)
            time.sleep(1)

        return {
            "user_id": int(user_id),
            "user_name": user_name,
            "illusts": illust_collect,
        }

    def process_illusts(self, UserIllusts: list[UserIllust], root_path: Path):
        root_path = root_path.joinpath("illusts")

        for userIllust in UserIllusts:
            path = utils.create_folder_path(
                root_path=root_path,
                id=userIllust.get("user_id"),
                name=userIllust.get("user_name"),
                logger=self.logger,
            )

            self.logger.info(f"Start Processing illusts from {userIllust.get('user_name')}")

            count = 0
            for illust in userIllust.get("illusts"):
                illust_id = illust.get("id")

                with SQLiteDB() as db:
                    c = db.cursor()
                    c.execute("SELECT id FROM illust WHERE id = ?", (illust_id,))
                    if c.fetchone():
                        continue

                    illust_title = illust.get("title")
                    illust_user_id = illust.get("user_id")

                    try:
                        self.logger.info(f"Processing illust {illust_id}_{illust_title}")
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
                f"Success add {count} illust from {userIllust.get('user_name')}"
                if count > 0
                else f"No new illust from {userIllust.get('user_name')}"
            )

    def download_illust(self, illust: Illust, root_path: Path):
        id = illust.get("id")
        title = utils.normalize_name(illust.get("title"))
        urls = illust.get("image_urls")

        if len(urls) > 1:
            root_path = utils.create_folder_path(root_path=root_path, id=id, name=title, logger=self.logger)

        for url in urls:
            file_name = f"{title}_{url.split('/').pop()}"
            file_path = root_path.joinpath(file_name)
            if file_path.exists():
                continue

            utils.download_file(file_path, url)
            utils.fix_img_datetime(file_path, illust.get("create_date"))

    def collect_novels(self, user_id: int | str, user_name: str):
        collect: tuple[list[Novel], list[NovelSeries]] = ([], [])

        self.logger.info(f"Collecting novels from user {user_name}_{user_id}")

        series_set = set()
        qs: Qs = {"user_id": user_id}
        while qs:
            r = self.user_novels(**qs)
            next_url = r.get("next_url")
            novels = r.get("novels")

            if novels is None:
                self.logger.error(f"Failed to collect novels from user {user_id}, novels is none")
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
                            "user_name": novel.get("user").get("name"),
                            "cover_url": novel.get("image_urls").get("large"),
                        }
                    )
                elif not series_id:
                    collect[0].append(
                        {
                            "id": novel.get("id"),
                            "title": novel.get("title"),
                            "user_id": novel.get("user").get("id"),
                            "user_name": novel.get("user").get("name"),
                        }
                    )

            qs = self.parse_qs(next_url)
            time.sleep(1)

        # 0 = novel, 1 = series
        return collect

    def process_novels(self, novels: list[Novel], root_path: Path):
        root_path = root_path.joinpath("novels")

        for novel in novels:
            path = utils.create_folder_path(
                root_path=root_path, id=novel.get("user_id"), name=novel.get("user_name"), logger=self.logger
            )

            novel_id = novel.get("id")

            with SQLiteDB() as db:
                c = db.cursor()
                c.execute("SELECT id FROM novel WHERE id = ?", (novel_id,))
                if c.fetchone():
                    continue

                self.logger.info(f"Processing novel {novel.get('id')}, {novel.get('title')}")
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

    def process_novels_series(self, series_list: list[NovelSeries], root_path: Path):
        root_path = root_path.joinpath("novels")

        for series in series_list:
            path = utils.create_folder_path(
                root_path=root_path, id=series.get("user_id"), name=series.get("user_name"), logger=self.logger
            )

            qs: Qs = {"series_id": series.get("id")}
            no = 0

            while qs:
                r = self.novel_series(**qs)
                next_url = r.get("next_url")
                novels = r.get("novels")

                if novels is None:
                    self.logger.error(f"Failed to process series {series}, novels is none")
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
                        "user_name": series.get("user_name"),
                    }

                    with SQLiteDB() as db:
                        c = db.cursor()
                        c.execute("SELECT id FROM novel WHERE id = ?", (novel_id,))
                        if c.fetchone():
                            continue

                        self.logger.info(f"Processing series {series.get('id')}, novel: {novel_title}")
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
                            self.logger.error(f"Failed to download {series.get('id')}, novel no {no}: {e}")
                            continue

                qs = self.parse_qs(next_url)
                time.sleep(1)

    def download_novel(
        self,
        novel: Novel,
        root_path: Path,
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
            utils.create_folder_path(
                root_path=root_path,
                id=series_id,
                name=series_title,
                logger=self.logger,
            )

            utils.download_file(
                root_path.joinpath(f"{series_title}.jpg"),
                cover_url.replace("c/240x480_80", ""),
            )

        novel_text = self.novel_text(id).get("text")

        max_bytes = 250
        encoded = title.encode("utf-8")
        if len(encoded) > max_bytes:
            cut = encoded[:max_bytes]
            while True:
                try:
                    title = cut.decode("utf-8")
                    break
                except UnicodeDecodeError:
                    cut = cut[:-1]

        file_path = root_path.joinpath(f"{title}.txt")
        with file_path.open("w", encoding="utf-8") as f:
            for line in novel_text.strip().split("\n"):
                f.write(line.strip() + "\n")
