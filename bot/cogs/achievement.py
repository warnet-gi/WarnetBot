import discord
from discord import Interaction, app_commands, Embed
from discord.ext import commands
import Paginator

import json
from typing import List, Dict

from bot.bot import WarnetBot


ACHIEVEMENT_DATA_PATH = 'bot/data/achievement.json'

class Achievement(commands.Cog):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.achievement_data = self.get_achievement_json_data()
        self._total_achievement_data = len(self.achievement_data)
        self.achievement_embeds = self.prepare_achievement_embeds()

    @app_commands.command(name='achievement-member-register', description='Member need to register before using other achievement commands')
    async def achievement_register(self, interaction: Interaction) -> None:

        pass

    @app_commands.command(name='achievement-list', description='Shows all available achievement list')
    async def achievement_list(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        await Paginator.Simple().start(interaction, pages=self.achievement_embeds)

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
    def get_achievement_json_data() -> Dict[str, Dict[str, str]]:
        with open(ACHIEVEMENT_DATA_PATH, 'r') as f:
            data = json.load(f)
        
        return data['data']

    def prepare_achievement_embeds(self) -> List[Embed]:
        total_data = self._total_achievement_data
        total_pages = total_data//10 + 1 if total_data % 10 else total_data//10

        embeds = []
        for page in range(total_pages):
            embed = discord.Embed(
                color=0xfcba03,
                title='WARNET Achievement List',
                description='Berikut daftar achievement yang tersedia di server ini:'
            )
            embed.set_footer(text='Gunakan command /achievement-detail untuk melihat detail achievement')

            id_start = 10*page + 1
            id_end = 10*(page+1)
            for achievement_id in range(id_start, id_end+1):
                data = self.achievement_data[str(achievement_id)]
                embed.add_field(name=f"`{achievement_id}` {data['name']}", value=f"```{data['desc']}```", inline=True)

            embeds.append(embed)
        
        return embeds


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Achievement(bot))