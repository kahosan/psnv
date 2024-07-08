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
