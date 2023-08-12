from typing import Optional

from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot


@commands.guild_only()
class Color(commands.GroupCog, group_name='warnet-color'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    color_add = app_commands.Group(name='add', description='Sub command to handle role creation.')
    color_edit = app_commands.Group(name='edit', description='Sub command to handle role editing.')

    @color_add.command(name='hex')
    async def add_hex_color(self, interaction: Interaction, name: str, hex: str) -> None:
        pass

    @color_add.command(name='rgb')
    async def add_rgb_color(self, interaction: Interaction, name: str, r: int, g: int, b: int) -> None:
        pass

    @color_edit.command(name='hex')
    async def edit_hex_color(
        self, interaction: Interaction, new_name: str, hex: str, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @color_edit.command(name='rgb')
    async def edit_rgb_color(
        self, interaction: Interaction, new_name: str, r: int, g: int, b: int, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @app_commands.command(name='set')
    async def set_color(self, interaction: Interaction, name: Optional[str], number: Optional[int]) -> None:
        pass

    @app_commands.command(name='remove')
    async def remove_color(self, interaction: Interaction, name: Optional[str], number: Optional[int]) -> None:
        pass

    @app_commands.command(name='list')
    async def list_color(self, interaction: Interaction) -> None:
        pass

    @app_commands.command(name='info')
    async def info_color(self, interaction: Interaction, name: Optional[str], number: Optional[int]) -> None:
        pass

    @app_commands.command(name='delete')
    async def delete_color(self, interaction: Interaction, name: Optional[str], number: Optional[int]) -> None:
        pass

    @app_commands.command(name='help')
    async def help_color(self, interaction: Interaction) -> None:
        pass


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Color(bot))
