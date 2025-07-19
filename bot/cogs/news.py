import asyncio
import datetime
import json
import logging
from pathlib import Path

import discord
import pytz
from anyio import open_file
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
        news = hoyolab_news()
        info_channel = self.bot.get_channel(news_config.INFORMATION_CHANNEL_ID)
        if info_channel is None:
            logger.error(
                "info channel is none",
                extra={"channel_id": news_config.INFORMATION_CHANNEL_ID},
            )
            return

        async with await open_file(
            news_config.LAST_ID_HOYOLAB_NEWS_PATH, encoding="utf-8"
        ) as f:
            contents = await f.read()
            last_id = contents.strip()

        await news.create_feed()

        if not news.was_updated and last_id != "":
            logger.info("[hoyolab] No new news updates found.")
            return

        async with await open_file(
            news_config.JSON_HOYOLAB_NEWS_PATH, encoding="utf-8"
        ) as f:
            contents = await f.read()
            news_json: HoyolabNews = json.loads(contents)
            news_data = news_json["items"]

        start_index = None
        for i, item in enumerate(news_data):
            if item["id"] == last_id:
                start_index = i
                break

        new_news = news_data if start_index is None else news_data[:start_index]

        for item in reversed(new_news):
            embed = discord.Embed(
                title=item["title"],
                url=item["url"],
                color=news_config.TAG_COLOR_MAP.get(
                    item["tags"][0].value, discord.Color.default()
                ),
                timestamp=item["date_published"],
            )
            embed.set_image(url=item["image"])
            embed.set_author(
                name=f"Hoyolab - {item['tags'][0]}",
                icon_url="https://www.hoyolab.com/favicon.ico",
            )
            await info_channel.send(embed=embed)

            await asyncio.sleep(1)

        async with await open_file(
            news_config.LAST_ID_HOYOLAB_NEWS_PATH, "w", encoding="utf-8"
        ) as f:
            await f.write(str(news_data[0]["id"]))

        logger.info("[hoyolab] Successfully sent news updates to the channel.")
        return

    @_news_hoyolab.before_loop
    async def _before_news_hoyolab(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(News(bot))
