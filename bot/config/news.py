import datetime

import discord

from bot import config

INFORMATION_CHANNEL_ID = 774322083319775262 if config.BOT_DEBUG else 829136309271527434

JSON_GENSHIN_NEWS_PATH = "bot/data/news/genshin.json"
LAST_ID_GENSHIN_NEWS_PATH = "bot/data/news/genshin.txt"

JSON_HOYOLAB_NEWS_PATH = "bot/data/news/hoyolab.json"
LAST_ID_HOYOLAB_NEWS_PATH = "bot/data/news/hoyolab.txt"

utc = datetime.timezone.utc

# Repeat every 10 minutes with an offset of 2 minutes
TIMES_CHECK_UPDATE = [
    datetime.time(hour=h, minute=m, tzinfo=utc) for h in range(24) for m in range(2, 60, 10)
]

TAG_COLOR_MAP = {
    "Info": discord.Color.blue(),
    "Events": discord.Color.green(),
    "Updates": discord.Color.gold(),
    "Notices": discord.Color.gold(),
}
CHAN_ID_MAP = {
    "396": "Info",
    "397": "Updates",
    "398": "Events",
}
