import asyncio
import io
import logging
from datetime import datetime, time, timedelta, timezone

import aiohttp
import discord
import pytz
from discord.ext import commands, tasks

from bot.bot import TatsuApi, WarnetBot
from bot.cogs.ext.booster.exp import give_monthly_booster_exp
from bot.config import (
    ADMIN_CHANNEL_ID,
    ANNOUNCEMENT_CHANNEL_ID,
    BOOSTER_MONTHLY_EXP,
    BOOSTER_ROLE_ID,
    GUILD_ID,
    TATSU_LOG_CHANNEL_ID,
)

logger = logging.getLogger(__name__)


class Booster(commands.Cog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._monthly_booster.start()

    @commands.is_owner()
    @commands.command(name='boostermonthly')
    async def manual_monthly_booster(self, ctx: commands.Context) -> None:
        await ctx.typing()

        msg = await ctx.send("please react with ✅ to approve this action.")
        await msg.add_reaction("✅")

        approved = set()
        owner_ids = set(self.bot.owner_ids)

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "✅"
                and user.id in owner_ids
            )

        try:
            while len(approved) != len(owner_ids):
                _, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                approved.add(user.id)
        except asyncio.TimeoutError:
            await ctx.send("Timeout! Action cancelled.")
            return

        logger.info(
            f'manual monthly exp booster is triggered: {datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%B %Y")}'
        )
        await give_monthly_booster_exp(self.bot)

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone(timedelta(hours=7))))
    async def _monthly_booster(self) -> None:
        date = datetime.now(pytz.timezone('Asia/Jakarta'))
        if date.day == 1:
            await give_monthly_booster_exp(self.bot)

    @_monthly_booster.before_loop
    async def _before_monthly_booster(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Booster(bot))
