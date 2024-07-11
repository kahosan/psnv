import os


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


def check_folder_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def download_file(path: str, url: str):
    import requests

    with requests.get(
        url, headers={"Referer": "https://app-api.pixiv.net/"}, stream=True
    ) as r:
        r.raise_for_status()
        with open(path, "wb") as file:
            for chunk in r.iter_content(chunk_size=8192):
                file.write(chunk)
