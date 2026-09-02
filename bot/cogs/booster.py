import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

import pytz
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.booster.exp import give_monthly_booster_exp
from bot.helper import ensure_task_started, handle_cog_error, value_is_none

logger = logging.getLogger(__name__)


class Booster(commands.Cog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        ensure_task_started(self._monthly_booster)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        await handle_cog_error(ctx, error, "Booster")

    @commands.command(name="boostermonthly")
    @commands.is_owner()
    async def manual_monthly_booster(self, ctx: commands.Context) -> None:
        await ctx.typing()

        msg = await ctx.send("please react with ✅ to approve this action.")
        await msg.add_reaction("✅")

        approved = set()

        if self.bot.owner_ids is None:
            await value_is_none("owners", ctx=ctx)
            return
        owner_ids = set(self.bot.owner_ids)

        def check(reaction, user):  # noqa: ANN001, ANN202 intended design
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "✅"
                and user.id in owner_ids
            )

        try:
            while not approved.intersection(owner_ids):
                _, user = await self.bot.wait_for(
                    "reaction_add", timeout=300.0, check=check
                )
                approved.add(user.id)
        except asyncio.TimeoutError:  # noqa: UP041 - explicit asyncio timeout for clarity
            await ctx.send("Timeout! Action cancelled.")
            return

        logger.info(
            "Manual monthly exp booster is triggered",
            extra={
                "time": datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%B %Y")
            },
        )
        await give_monthly_booster_exp(self.bot)

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone(timedelta(hours=7))))
    async def _monthly_booster(self) -> None:
        date = datetime.now(pytz.timezone("Asia/Jakarta"))
        if date.day == 1:
            await give_monthly_booster_exp(self.bot)

    @_monthly_booster.before_loop
    async def _before_monthly_booster(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Booster(bot))
