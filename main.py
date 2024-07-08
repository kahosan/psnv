from core.logger import Logger
from core.config import load_config
from core.pixiv import Illust, Pixiv


logger = Logger(logger_name="main").get_logger()
config = load_config()


p = Pixiv(refresh_token=config.get("refresh_token"))
follow_config = config.get("follow")


if follow_config.get("enabled"):
    type_config = follow_config.get("type")
    root_path = follow_config.get("save_path")

    user_ids = p.get_follow_ids(p.user_id)
    if type_config.get("illust"):
        illusts: list[Illust] = []
        for id in user_ids:
            illusts.extend(p.collect_illusts(id, type="illust"))
        p.process_illusts(illusts=illusts, root_path=root_path)
