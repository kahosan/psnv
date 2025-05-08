import logging
from pathlib import Path


def normalize_name(name: str):
    return (
        name.replace("\\", "╲")
        .replace("/", "／")
        .replace(":", "：")
        .replace("*", "⚝")
        .replace("?", "？")
        .replace('"', "''")
        .replace("<", "‹")
        .replace(">", "›")
        .replace("|", "｜")
    )


def check_folder_exists(path: Path):
    if not path.exists():
        path.mkdir(parents=True)


def check_user_name_is_change(current_name: str, user_id: int, root_path: Path):
    for folder in root_path.iterdir():
        folder_name = folder.name
        if "_" in folder_name:
            name, id = folder_name.split("_")
            if id == user_id and name != current_name:
                return True, name
    return False, None


def sync_user_name_folder(current_name: str, user_id: int, root_path: Path, logger: logging.Logger):
    (is_change, old_name) = check_user_name_is_change(current_name, user_id, root_path)
    if is_change is False:
        return

    new_folder_name = f"{current_name}_{user_id}"
    old_folder_name = f"{old_name}_{user_id}"
    try:
        Path.rename(
            root_path.joinpath(old_folder_name),
            root_path.joinpath(new_folder_name),
        )
        logger.info(f"Renamed folder: {old_folder_name} -> {new_folder_name}")
    except Exception as e:
        logger.error(f"Error while renaming folder: {e}")


def download_file(file_path: Path, url: str):
    import requests

    headers = {
        "Referer": "https://app-api.pixiv.net/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with file_path.open("wb") as file:
            for chunk in r.iter_content(chunk_size=8192):
                file.write(chunk)
