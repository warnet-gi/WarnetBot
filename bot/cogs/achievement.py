import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands

import json

from bot.bot import WarnetBot


ACHIEVEMENT_DATA_PATH = 'bot/data/achievement.json'

class Achievement(commands.Cog):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.achievement_data = self.get_achievement_json_data()

    @app_commands.command(name='achievement-member-register', description='Member need to register before using other achievement commands')
    async def achievement_register(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement-list', description='Shows all available achievement list')
    async def achievement_list(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        
        embed = discord.Embed(
            color=0xfcba03,
            title='WARNET Achievement List',
            description='Berikut daftar achievement yang tersedia di server ini:'
        )
        
        for data in self.achievement_data['data']:
            embed.add_field(name=f"`{data['id']}` {data['name']}", value=f"```{data['desc']}```", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name='achievement-detail', description='Shows the detail of an achievement')
    async def achievement_detail(self, interaction: Interaction, achievement_id: int) -> None:
        
        pass

    @app_commands.command(name='achievement-stats', description='Shows your completed achievement stats')
    async def achievement_stats(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement-give', description='Admin or Mod can mark an achievement as complete')
    async def achievement_give(self, interaction: Interaction, achievement_id: int) -> None:

        pass
    
    @app_commands.command(name='achievement-ungive', description='Admin or Mod can mark an achievement as incomplete')
    async def achievement_ungive(self, interaction: Interaction, achievement_id: int) -> None:

        pass

    @staticmethod
    def get_achievement_json_data() -> dict:
        with open(ACHIEVEMENT_DATA_PATH, 'r') as f:
            data = json.load(f)
        
        return data


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Achievement(bot))