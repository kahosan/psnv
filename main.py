from core.config import load_config
from core.pixiv import UserIllust, Novel, NovelSeries, Pixiv


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
        illusts: list[UserIllust] = []
        for id in user_ids:
            illusts.extend(p.collect_illusts(id))
        p.process_illusts(UserIllusts=illusts, root_path=root_path)

    if type_config.get("novel"):
        single_novels: list[Novel] = []
        novel_series: list[NovelSeries] = []
        for id in user_ids:
            _novels = p.collect_novels(id)
            single_novels.extend(_novels[0])
            novel_series.extend(_novels[1])
        p.process_novels_series(series_list=novel_series, root_path=root_path)
        p.process_novels(novels=single_novels, root_path=root_path)


if favorite_config.get("enabled"):
    pass


if ranking_config.get("enabled"):
    pass
