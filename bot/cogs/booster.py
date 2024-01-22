import asyncio
import io
from datetime import datetime, time, timedelta, timezone

import discord
import pytz
from discord.ext import commands, tasks

from bot.bot import TatsuApi, WarnetBot
from bot.config import (
    ADMIN_CHANNEL_ID,
    BOOSTER_MONTHLY_EXP,
    BOOSTER_ROLE_ID,
    GUILD_ID,
    TATSU_LOG_CHANNEL_ID,
)


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
            admin_channel = self.bot.get_channel(ADMIN_CHANNEL_ID)
            tatsu_log_channel = self.bot.get_channel(TATSU_LOG_CHANNEL_ID)
            guild = self.bot.get_guild(GUILD_ID)
            role = guild.get_role(BOOSTER_ROLE_ID)
            month = date.strftime("%B")
            member_tag = member_id = ''

            for member in role.members:
                await TatsuApi().add_score(member.id, BOOSTER_MONTHLY_EXP)
                member_tag += f"{member.mention}, "
                member_id += f"{member.id} "
                await asyncio.sleep(1.5)

            embed = discord.Embed(
                title="<a:checklist:1077585402422112297> Score updated!",
                description=f"Successfully awarded `{BOOSTER_MONTHLY_EXP}` score to {role.mention}> ({len(role.members)} members)\n\n{member_tag}",
                timestamp=datetime.now(),
                colour=0x17A168,
            )
            embed.set_footer(
                text="Warnet",
                icon_url="https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png",
            )
            await tatsu_log_channel.send(embed=embed)

            buffer = io.BytesIO(member_id.encode('utf-8'))
            file = discord.File(buffer, filename=f"{month}_honorary.txt")
            await admin_channel.send(
                content=f"Exp Honorary Bulanan Sudah dibagikan, jangan lupa Announcement.\nlog honorary bulan {month}",
                file=file,
            )

    @_monthly_booster.before_loop
    async def _before_monthly_booster(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Booster(bot))
