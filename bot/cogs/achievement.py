import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands

from bot.bot import WarnetBot


class Achievement(commands.Cog):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @app_commands.command(name='achievement member register', description='Member need to register before using other achievement commands')
    async def achievement_register(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement list', description='Shows all available achievement list')
    async def achievement_list(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement stats', description='Shows your completed achievement stats')
    async def achievement_stats(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement give', description='Admin or Mod can mark an achievement as complete')
    async def achievement_give(self, interaction: Interaction, achievement_id: int) -> None:

        pass
    
    @app_commands.command(name='achievement ungive', description='Admin or Mod can mark an achievement as incomplete')
    async def achievement_ungive(self, interaction: Interaction, achievement_id: int) -> None:

        pass


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Achievement(bot))