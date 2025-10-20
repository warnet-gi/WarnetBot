import logging
import logging.handlers
import sys
from datetime import datetime

from pytz import timezone


class DebugConsoleHandler(logging.StreamHandler):
    def __init__(self) -> None:
        super().__init__(stream=sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno != logging.DEBUG:
            return
        if record.name.startswith("discord"):
            return
        super().emit(record)


def setup_logger() -> None:
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    console_handler = DebugConsoleHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="bot/data/log/bot.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logging.Formatter.converter = lambda *args: datetime.now(  # noqa: ARG005
        timezone("Asia/Jakarta")
    ).timetuple()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
