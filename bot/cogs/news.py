import asyncio
import datetime
import json
import logging
import os

import discord
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.news.genshin import get_genshin_news
from bot.cogs.ext.news.hoyolab import hoyolab_news
from bot.config import news as news_config

logger = logging.getLogger(__name__)


class News(commands.GroupCog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not os.path.exists(news_config.LAST_ID_GENSHIN_NEWS_PATH):
            with open(news_config.LAST_ID_GENSHIN_NEWS_PATH, "w", encoding="utf-8") as f:
                f.write("")

        if not os.path.exists(news_config.LAST_ID_HOYOLAB_NEWS_PATH):
            with open(news_config.LAST_ID_HOYOLAB_NEWS_PATH, "w", encoding="utf-8") as f:
                f.write("")

        if not self._news_hoyolab.is_running():
            self._news_hoyolab.start()
        if not self._news_genshin.is_running():
            self._news_genshin.start()

    @tasks.loop(time=news_config.TIMES_CHECK_UPDATE)
    async def _news_genshin(self) -> None:
        info_channel = self.bot.get_channel(news_config.INFORMATION_CHANNEL_ID)

        try:
            await get_genshin_news()
        except Exception as e:
            logger.error(f"[genshin] Failed to fetch Genshin news: {e}")
            return

        with open(news_config.LAST_ID_GENSHIN_NEWS_PATH, "r", encoding="utf-8") as f:
            last_id = f.read().strip()

        with open(news_config.JSON_GENSHIN_NEWS_PATH, "r", encoding="utf-8") as f:
            news_data = json.load(f)["data"]["list"]

        last_json_id = str(news_data[0]["iInfoId"])
        if last_json_id == last_id:
            logger.info("[genshin] No new news updates found.")
            return

        start_index = None
        for i, item in enumerate(news_data):
            if str(item["iInfoId"]) == last_id:
                start_index = i
                break

        if start_index is None:
            new_news = news_data
        else:
            new_news = news_data[:start_index]

        for item in reversed(new_news):
            s_chan_ids = item.get("sChanId", [])
            if len(s_chan_ids) > 1:
                current_tag = "Info"
            else:
                current_tag = news_config.CHAN_ID_MAP.get(s_chan_ids[0], "Info") if s_chan_ids else "Info"

            embed = discord.Embed(
                title=item["sTitle"],
                description=item["sIntro"],
                url=f"https://genshin.hoyoverse.com/en/news/detail/{item['iInfoId']}",
                color=news_config.TAG_COLOR_MAP.get(current_tag, discord.Color.default()),
            )

            image_url = None
            try:
                s_ext = json.loads(item.get("sExt", "{}"))
                banners = s_ext.get("banner", [])
                if banners and "url" in banners[0]:
                    image_url = banners[0]["url"]
            except Exception as e:
                logger.error(f"[genshin] Error parsing image URL: {e}")
            if image_url:
                embed.set_image(url=image_url)

            embed.set_author(
                name=f"Genshin Impact News - {current_tag}",
                icon_url="https://cdn.discordapp.com/icons/522681957373575168/84a7500128d64ca60e959799c3e66f21.webp",
            )
            embed.timestamp = datetime.datetime.fromisoformat(item["dtCreateTime"])

            await info_channel.send(embed=embed)
            await asyncio.sleep(1)

        with open(news_config.LAST_ID_GENSHIN_NEWS_PATH, "w", encoding="utf-8") as f:
            f.write(last_json_id)

    @_news_genshin.before_loop
    async def _before_news_genshin(self):
        await self.bot.wait_until_ready()

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
