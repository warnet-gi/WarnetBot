import logging
import logging.handlers
from datetime import datetime

from pytz import timezone

handler = logging.handlers.RotatingFileHandler(
    filename='bot/data/bot.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=5,
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
logging.Formatter.converter = lambda *args: datetime.now(timezone('Asia/Jakarta')).timetuple()
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
