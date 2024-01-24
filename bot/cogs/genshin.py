import json
import logging
import re

import discord
import feedparser
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.config import genshin as genshin_config

logger = logging.getLogger(__name__)


@commands.guild_only()
class Genshin(commands.GroupCog, group_name="genshin"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._rss.start()

    @tasks.loop(minutes=2)
    async def _rss(self) -> None:
        info_channel = self.bot.get_channel(genshin_config.INFORMATION_CHANNEL_ID)

        with open(genshin_config.RSS_PUBLISHED_ID_DATA_PATH) as f:
            data = json.load(f)
            latest_entry_id = data['rss']['latest_pub_id']

        feed = feedparser.parse(genshin_config.RSS_FEED_URL)
        new_entry = feed.entries[0]
        if new_entry.id != latest_entry_id:
            logger.info(f'NEW GENSHIN ARTICLE FOUND! ID={new_entry.id}')

            data['rss']['latest_pub_id'] = new_entry.id
            with open(genshin_config.RSS_PUBLISHED_ID_DATA_PATH, 'w') as f:
                json.dump(data, f, indent=4)

            pattern = re.compile(r'src="(https://.+\.(?:jpg|png))"')
            try:
                entry_image_link = pattern.search(new_entry.content[0].value).group(1)
            except AttributeError:
                entry_image_link = None

            embed = discord.Embed(
                title=new_entry.title,
                url=new_entry.link,
                description=new_entry.summary,
                color=discord.Color.dark_embed(),
            )
            embed.set_image(url=entry_image_link)
            await info_channel.send(embed=embed)

    @_rss.before_loop
    async def _before_rss(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Genshin(bot))
