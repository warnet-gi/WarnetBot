import discord
from discord import Interaction, app_commands, Embed
from discord.ext import commands

import json
import datetime
from typing import List, Dict, Optional

from bot.bot import WarnetBot
from bot.config import config
from bot.cogs.achievement_ext.member import (
    register,
    show_achievement_list,
    show_achievement_detail,
    show_achievement_stats,
)
from bot.cogs.achievement_ext.admin import give_achievement, revoke_achievement


ACHIEVEMENT_DATA_PATH = 'bot/data/achievement.json'
PRIVATE_DEV_GUILD_ID = config.PRIVATE_DEV_GUILD_ID
WARNET_GUILD_ID = config.WARNET_GUILD_ID

class Achievement(commands.GroupCog, group_name="achievement"):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.achievement_data = self.get_achievement_json_data()
        self._total_achievement_data = len(self.achievement_data)
        self.achievement_embeds = self.prepare_achievement_embeds()

    @app_commands.command(name='member-register', description='Member need to register before using other achievement commands')
    async def achievement_register(self, interaction: Interaction) -> None:
        await register(self, interaction)

    @app_commands.command(name='list', description='Shows all available achievement list')
    async def achievement_list(self, interaction: Interaction) -> None:
        await show_achievement_list(self, interaction)

    @app_commands.command(name='detail', description='Shows the detail of an achievement')
    async def achievement_detail(self, interaction: Interaction, achievement_id: int) -> None:
        await show_achievement_detail(self, interaction, achievement_id)
        
    @app_commands.command(name='stats', description='Shows your completed achievement stats')
    async def achievement_stats(self, interaction: Interaction) -> None:
        await show_achievement_stats(self, interaction)
        
    # TODO: If the amount of completed achievement pass a certain amount -> give special role
    @app_commands.command(name='give', description='Admin or Mod can mark an achievement as complete for specific user')
    async def achievement_give(self, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
        await give_achievement(self, interaction, member, achievement_id)
        
    # TODO: If the amount of completed achievement is below a certain amount -> remove special role
    @app_commands.command(name='revoke', description='Admin or Mod can mark an achievement as incomplete')
    async def achievement_revoke(self, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
        await revoke_achievement(self, interaction, member, achievement_id)

    @staticmethod
    def get_achievement_json_data() -> Dict[str, Dict[str, str]]:
        with open(ACHIEVEMENT_DATA_PATH, 'r') as f:
            data = json.load(f)
        
        return data['data']

    @staticmethod
    def get_achievement_badge_id(total_achievement: int) -> Optional[int]:
        """
        return achievement role id based on total completed achievement
        """

        if total_achievement < 10:
            return None
        elif total_achievement < 20:
            return config.ACHIEVEMENT_RANK_ROLE_ID[0]
        elif total_achievement < 50:
            return config.ACHIEVEMENT_RANK_ROLE_ID[1]
        elif total_achievement < 80:
            return config.ACHIEVEMENT_RANK_ROLE_ID[2]
        elif total_achievement < 150:
            return config.ACHIEVEMENT_RANK_ROLE_ID[3]
        else:
            return config.ACHIEVEMENT_RANK_ROLE_ID[4]

    def prepare_achievement_embeds(self) -> List[Embed]:
        total_data = self._total_achievement_data
        total_pages = total_data//10 + 1 if total_data % 10 else total_data//10

        embeds = []
        for page in range(total_pages):
            embed = discord.Embed(
                color=0xfcba03,
                title='WARNET Achievement List',
                description='Berikut daftar achievement yang tersedia di server ini:',
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text='Gunakan command /achievement-detail untuk melihat detail achievement')

            id_start = 10*page + 1
            id_end = 10*(page+1)
            for achievement_id in range(id_start, id_end+1):
                data = self.achievement_data[str(achievement_id)]
                embed.add_field(name=f"🏅`{achievement_id}` {data['name']}", value=f"```{data['desc']}```", inline=False)

            embeds.append(embed)
        
        return embeds


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(
        Achievement(bot),
        guilds=[discord.Object(PRIVATE_DEV_GUILD_ID), discord.Object(WARNET_GUILD_ID)]
    )