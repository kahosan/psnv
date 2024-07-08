import sqlite3


class SQLiteDB:
    def __init__(self):
        self.__instance = sqlite3.connect("pixiv.db")
        self.__instance.cursor().execute(
            "CREATE TABLE IF NOT EXISTS illust (id INTEGER PRIMARY KEY, title TEXT, user_id INTEGER)"
        )

    def __del__(self):
        self.__instance.close()

    def __enter__(self) -> sqlite3.Connection:
        return self.__instance

    def __exit__(self, exc_type, exc_value, traceback):
        self.__instance.close()
