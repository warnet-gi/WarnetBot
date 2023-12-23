import io
from datetime import datetime, time, timedelta, timezone

import discord
import pytz
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.config import BOOSTER_ROLE_ID, GUILD_ID, ADMIN_CHANNEL_ID


class Booster(commands.Cog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._monthly_booster.start()

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone(timedelta(hours=7))))
    async def _monthly_booster(self) -> None:
        date = datetime.now(pytz.timezone('Asia/Jakarta'))
        if date.day == 1:
            channel = self.bot.get_channel(ADMIN_CHANNEL_ID)
            guild = self.bot.get_guild(GUILD_ID)
            role = guild.get_role(BOOSTER_ROLE_ID)
            members_content = ''
            for member in role.members:
                members_content += f"{member.id} "
            buffer = io.BytesIO(members_content.encode('utf-8'))
            file = discord.File(buffer, filename="honorary.txt")
            await channel.send(file=file)

    @_monthly_booster.before_loop
    async def _before_monthly_booster(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Booster(bot))
