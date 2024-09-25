import os
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARN,
    WARNING,
    FileHandler,
    Formatter,
    getLogger,
    Logger as LoggerAlias,
)
from time import localtime, strftime
from typing import Optional

from rich.logging import RichHandler

DEFAULT_LOG_FOLDER = os.path.join(os.getcwd(), "logs")


class Logger:
    NAME_TO_LEVEL = {
        "INFO": INFO,
        "DEBUG": DEBUG,
        "WARN": WARN,
        "WARNING": WARNING,
        "ERROR": ERROR,
        "CRITICAL": CRITICAL,
    }

    def __init__(
        self,
        logger_level: str = "INFO",
        logger_name: Optional[str] = "logger",
        log_dir: Optional[str] = None,
        log_filename: Optional[str] = None,
    ):
        self.logger: LoggerAlias
        self.level = self.NAME_TO_LEVEL.get(logger_level, "INFO")
        self.name = logger_name
        self.log_dir = log_dir or DEFAULT_LOG_FOLDER
        self.log_filename = log_filename or strftime("%Y-%m-%d", localtime())
        self._set_logger()

    def _set_logger(self) -> None:
        try:
            os.makedirs(self.log_dir)
        except (FileExistsError, OSError):
            pass

        self.logger = getLogger(self.name)

        # HANDLERS
        # If stream is not specified, sys.stderr is used.
        # If you need sys.stdout, pass it to StreamHandler constructor()
        # stream_handler = StreamHandler()
        shell_handler = RichHandler(
            rich_tracebacks=True, show_level=False, show_time=False, show_path=False
        )

        file_handler = FileHandler(
            filename=os.path.join(self.log_dir, f"{self.log_filename}.log"),
            mode="a",
            encoding="utf-8",
        )

        # LOG LEVELS
        self.logger.setLevel(self.level)
        shell_handler.setLevel(self.level)
        file_handler.setLevel(self.level)

        # LOG FORMAT
        # fmt_shell = "%(name)s %(message)s"
        fmt_shell = (
            "[%(asctime)s] %(levelname)s | %(filename)s:%(lineno)d:   %(message)s"
        )
        fmt_file = (
            "[%(asctime)s] %(levelname)s | %(filename)s:%(lineno)d:   %(message)s"
        )
        datefmt = "%Y-%m-%d %H:%M:%S"

        # LOG FORMATTER
        # 2023-02-02,13:07:55 INFO     [logger2] Logging set up.             logger2.py:30
        # Warning: rich will add some logging formats to fmt_shell
        shell_formatter = Formatter(fmt_shell, datefmt)
        # [2023-02-02,13:07:55][ERROR][logger2][logger2.py:division:37] Oh noes!
        file_formatter = Formatter(fmt_file, datefmt)

        shell_handler.setFormatter(shell_formatter)
        file_handler.setFormatter(file_formatter)

        self.logger.handlers.clear()
        self.logger.addHandler(shell_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> LoggerAlias:
        return self.logger
