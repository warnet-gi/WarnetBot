import discord
from discord import Interaction, app_commands, Embed
from discord.ext import commands

from typing import Optional

from bot.bot import WarnetBot
from bot.config import config
from bot.cogs.ext.tcg.member import (
    register,
    member_stats,
)


PRIVATE_DEV_GUILD_ID = config.PRIVATE_DEV_GUILD_ID
WARNET_GUILD_ID = config.WARNET_GUILD_ID

@commands.guild_only()
class TCG(commands.GroupCog, group_name="tcg"):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @app_commands.command(name='register', description='Member need to register before using other tcg commands.')
    async def tcg_register(self, interaction: Interaction) -> None:
        await register(self, interaction)

    @app_commands.command(name='member-stats', description='Member can check their or someone else\'s TCG stats.')
    async def tcg_member_stats(self, interaction:Interaction, member: Optional[discord.Member]) -> None:
        await member_stats(self, interaction, member)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(
        TCG(bot),
        guilds=[discord.Object(PRIVATE_DEV_GUILD_ID), discord.Object(WARNET_GUILD_ID)]
    )