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
from bot.cogs.ext.news.genshin import GenshinNews, GenshinNewsSext, get_genshin_news
from bot.cogs.ext.news.hoyolab import HoyolabNews, hoyolab_news
from bot.config import news as news_config

logger = logging.getLogger(__name__)


class News(commands.GroupCog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not Path(news_config.LAST_ID_GENSHIN_NEWS_PATH).exists():
            async with await open_file(
                news_config.LAST_ID_GENSHIN_NEWS_PATH, "w", encoding="utf-8"
            ) as f:
                await f.write("")

        if not Path(news_config.LAST_ID_HOYOLAB_NEWS_PATH).exists():
            async with await open_file(
                news_config.LAST_ID_HOYOLAB_NEWS_PATH, "w", encoding="utf-8"
            ) as f:
                await f.write("")

        if not self._news_hoyolab.is_running():
            self._news_hoyolab.start()
        if not self._news_genshin.is_running():
            self._news_genshin.start()

    @tasks.loop(time=news_config.TIMES_CHECK_UPDATE)
    async def _news_genshin(self) -> None:
        info_channel = self.bot.get_channel(news_config.INFORMATION_CHANNEL_ID)
        if info_channel is None:
            logger.error(
                "info channel is none",
                extra={"channel_id": news_config.INFORMATION_CHANNEL_ID},
            )
            return

        try:
            await get_genshin_news()
        except Exception:
            logger.exception("[genshin] Exception occurred while fetching Genshin news")
            return

        async with await open_file(
            news_config.LAST_ID_GENSHIN_NEWS_PATH, encoding="utf-8"
        ) as f:
            content = await f.read()
            last_id = content.strip()

        async with await open_file(
            news_config.JSON_GENSHIN_NEWS_PATH, encoding="utf-8"
        ) as f:
            contents = await f.read()
            json_content: GenshinNews = json.loads(contents)
            news_data = json_content["data"]["list"]

        last_json_id = str(news_data[0]["iInfoId"])
        if last_json_id == last_id:
            logger.info("[genshin] No new news updates found.")
            return

        start_index = None
        for i, item in enumerate(news_data):
            if str(item["iInfoId"]) == last_id:
                start_index = i
                break

        new_news = news_data if start_index is None else news_data[:start_index]

        for item in reversed(new_news):
            s_chan_ids = item["sChanId"]
            if len(s_chan_ids) > 1:
                current_tag = "Info"
            else:
                current_tag = (
                    news_config.CHAN_ID_MAP.get(s_chan_ids[0], "Info")
                    if s_chan_ids
                    else "Info"
                )

            embed = discord.Embed(
                title=item["sTitle"],
                description=item["sIntro"],
                url=f"https://genshin.hoyoverse.com/en/news/detail/{item['iInfoId']}",
                color=news_config.TAG_COLOR_MAP.get(
                    current_tag, discord.Color.default()
                ),
            )

            image_url = None
            s_ext: GenshinNewsSext = json.loads(item["sExt"])
            image_url = s_ext["banner"][0]["url"]
            embed.set_image(url=image_url)

            embed.set_author(
                name=f"Genshin Impact News - {current_tag}",
                icon_url="https://cdn.discordapp.com/icons/522681957373575168/84a7500128d64ca60e959799c3e66f21.webp",
            )
            embed.timestamp = datetime.datetime.strptime(
                item["dtStartTime"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=pytz.timezone("Asia/Shanghai"))

            await info_channel.send(embed=embed)
            await asyncio.sleep(1)

        async with await open_file(
            news_config.LAST_ID_GENSHIN_NEWS_PATH, "w", encoding="utf-8"
        ) as f:
            await f.write(last_json_id)

    @_news_genshin.before_loop
    async def _before_news_genshin(self) -> None:
        await self.bot.wait_until_ready()

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
            )
            embed.set_image(url=item["image"])
            embed.set_author(
                name=f"Hoyolab - {item['tags'][0]}",
                icon_url="https://www.hoyolab.com/favicon.ico",
            )
            embed.timestamp = item["date_published"]
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
