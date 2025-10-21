import logging

from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.views.color_v2 import Components

logger = logging.getLogger(__name__)


@commands.guild_only()
class ColorV2(commands.GroupCog, group_name="warnet-colorv2"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @app_commands.command(name="test")
    async def testing(
        self,
        interaction: Interaction,
    ) -> None:
        view = Components()
        await interaction.response.send_message(view=view)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(ColorV2(bot))
