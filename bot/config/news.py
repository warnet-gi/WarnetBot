import datetime

import discord

from bot import config

INFORMATION_CHANNEL_ID = 774322083319775262 if config.BOT_DEBUG else 829136309271527434

JSON_HOYOLAB_NEWS_PATH = "bot/data/news/hoyolab.json"
LAST_ID_HOYOLAB_NEWS_PATH = "bot/data/news/hoyolab.txt"

# Repeat every 10 minutes with an offset of 2 minutes
TIMES_CHECK_UPDATE = [
    datetime.time(hour=h, minute=m, tzinfo=datetime.UTC)
    for h in range(1)
    for m in range(2, 60, 10)
]

TAG_COLOR_MAP = {
    "Info": discord.Color.blue(),
    "Events": discord.Color.green(),
    "Notices": discord.Color.gold(),
}
