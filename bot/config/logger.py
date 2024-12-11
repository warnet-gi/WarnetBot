import logging
import logging.handlers
import sys
from datetime import datetime
from pytz import timezone


class DebugConsoleHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(stream=sys.stdout)

    def emit(self, record):
        if record.levelno != logging.DEBUG:
            return
        if record.name.startswith("discord"):
            return
        super().emit(record)


def get_log_filename_daily():
    return datetime.now(timezone('Asia/Jakarta')).strftime("%Y-%m-%d") + ".log"


def setup_logger():
    formatter = logging.Formatter(
        '[{asctime}] [{levelname:<8}] {name}: {message}', datefmt="%Y-%m-%d %H:%M:%S", style='{'
    )

    console_handler = DebugConsoleHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="bot/data/log/" + get_log_filename_daily(),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logging.Formatter.converter = lambda *args: datetime.now(timezone('Asia/Jakarta')).timetuple()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
