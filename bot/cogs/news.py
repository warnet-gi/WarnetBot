import asyncio
import datetime
import json
import logging
import os

import discord
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.news.hoyolab import hoyolab_news
from bot.config import news as news_config

logger = logging.getLogger(__name__)


class News(commands.GroupCog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not os.path.exists(news_config.LAST_ID_HOYOLAB_NEWS_PATH):
            with open(news_config.LAST_ID_HOYOLAB_NEWS_PATH, "w", encoding="utf-8") as f:
                f.write("")

        if not self._news_hoyolab.is_running():
            self._news_hoyolab.start()

    @tasks.loop(time=news_config.TIMES_CHECK_UPDATE)
    async def _news_hoyolab(self) -> None:
        info_channel = self.bot.get_channel(news_config.INFORMATION_CHANNEL_ID)
        news = hoyolab_news()

        with open(news_config.LAST_ID_HOYOLAB_NEWS_PATH, "r", encoding="utf-8") as f:
            last_id = f.read().strip()

        await news.create_feed()

        if not news.was_updated and last_id != "":
            logger.info("[hoyolab] No new news updates found.")
            return

        with open(news_config.JSON_HOYOLAB_NEWS_PATH, "r", encoding="utf-8") as f:
            news_data = json.load(f)
            news_data = news_data["items"]

        start_index = None
        for i, item in enumerate(news_data):
            if item["id"] == last_id:
                start_index = i
                break

        if start_index is None:
            new_news = news_data
        else:
            new_news = news_data[:start_index]

        for item in reversed(new_news):
            embed = discord.Embed(
                title=item["title"],
                url=item["url"],
                color=news_config.TAG_COLOR_MAP.get(item["tags"][0], discord.Color.default()),
            )
            embed.set_image(url=item["image"])
            embed.set_author(
                name=f"Hoyolab - {item['tags'][0]}",
                icon_url="https://www.hoyolab.com/favicon.ico",
            )
            embed.timestamp = datetime.datetime.fromisoformat(item["date_published"])
            await info_channel.send(embed=embed)

            await asyncio.sleep(1)

        with open(news_config.LAST_ID_HOYOLAB_NEWS_PATH, "w", encoding="utf-8") as f:
            f.write(news_data[0]["id"])

        logger.info("[hoyolab] Successfully sent news updates to the channel.")
        return

    @_news_hoyolab.before_loop
    async def _before_news_hoyolab(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(News(bot))
