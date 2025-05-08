from pathlib import Path

from core.config import load_config
from core.pixiv import Novel, NovelSeries, Pixiv, UserIllust

config = load_config()
p = Pixiv(refresh_token=config.get("refresh_token"))


follow_config = config.get("follow")
favorite_config = config.get("favorite")
ranking_config = config.get("ranking")


if follow_config.get("enabled"):
    type_config = follow_config.get("type")
    root_path = Path(follow_config.get("save_path"))
    user_follows = p.get_user_follows(p.user_id)

    if type_config.get("illust"):
        illusts: list[UserIllust] = []
        for follow in user_follows:
            illusts.append(p.collect_illusts(follow.get("follow_id"), follow.get("follow_name")))
        p.process_illusts(UserIllusts=illusts, root_path=root_path)

    if type_config.get("novel"):
        single_novels: list[Novel] = []
        novel_series: list[NovelSeries] = []
        for follow in user_follows:
            _novels = p.collect_novels(follow.get("follow_id"))
            single_novels.extend(_novels[0])
            novel_series.extend(_novels[1])
        p.process_novels_series(series_list=novel_series, root_path=root_path)
        p.process_novels(novels=single_novels, root_path=root_path)


if favorite_config.get("enabled"):
    pass


if ranking_config.get("enabled"):
    pass
