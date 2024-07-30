from core.config import load_config
from core.pixiv import Illust, Novel, Pixiv


config = load_config()
p = Pixiv(refresh_token=config.get("refresh_token"))


follow_config = config.get("follow")
favorite_config = config.get("favorite")
ranking_config = config.get("ranking")


if follow_config.get("enabled"):
    type_config = follow_config.get("type")
    root_path = follow_config.get("save_path")
    user_ids = p.get_follow_ids(p.user_id)

    if type_config.get("illust"):
        illusts: list[Illust] = []
        for id in user_ids:
            illusts.extend(p.collect_illusts(id))
        p.process_illusts(illusts=illusts, root_path=root_path)

    if type_config.get("novel"):
        novels: list[Novel] = []
        for id in user_ids:
            novels.extend(p.collect_novels(id))
        p.process_novels(novels=novels, root_path=root_path)


if favorite_config.get("enabled"):
    pass


if ranking_config.get("enabled"):
    pass
