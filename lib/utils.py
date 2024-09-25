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

    headers = {
        "Referer": "https://app-api.pixiv.net/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as file:
            for chunk in r.iter_content(chunk_size=8192):
                file.write(chunk)
