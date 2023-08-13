from typing import Optional

import discord
from discord import Interaction, app_commands, Color as DiscordColor
from discord.ext import commands

from bot.bot import WarnetBot
from bot.config import config


@commands.guild_only()
class Color(commands.GroupCog, group_name='warnet-color'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    color_add = app_commands.Group(name='add', description='Sub command to handle role creation.')
    color_edit = app_commands.Group(name='edit', description='Sub command to handle role editing.')

    @color_add.command(name='hex')
    async def add_hex_color(self, interaction: Interaction, name: str, hex: str) -> None:
        try:
            hex = '#' + hex if not hex.startswith('#') else hex
            valid_color = DiscordColor.from_str(hex)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Please pass in a valid HEX code!\n\nExample: `#FFF456` or `FFF456`",
                ephemeral=True,
            )

        role_owner = interaction.user
        created_role = await interaction.guild.create_role(
            name=name,
            reason="Member Request",
            color=valid_color,
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO custom_role (role_id, owner_discord_id) VALUES ($1, $2)',
                created_role.id,
                role_owner.id,
            )

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(config.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

        # TODO
        # add created role data on memory so it can be used later

        embed = discord.Embed(
            color=valid_color, description=f'✅ Successfully created role: **{created_role.name}**.'
        )
        embed.add_field(
            name="What to do next?",
            value=(
                "- Use `/warnet-color list` to check list of all available custom roles\n"
                "- Use `/warnet-color set` to use your created role, or\n"
                "- Ask Admin/Mod to attach custom icon on your custom role (read <#822872937161162795> for instruction), or\n"
                "- Use `/warnet-color remove` to take off your current custom role, or\n"
                "- Use `/warnet-color edit hex/rgb` to edit your created custom role"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @color_add.command(name='rgb')
    async def add_rgb_color(
        self,
        interaction: Interaction,
        name: str,
        r: app_commands.Range[int, 0, 255],
        g: app_commands.Range[int, 0, 255],
        b: app_commands.Range[int, 0, 255],
    ) -> None:
        try:
            valid_color = DiscordColor.from_rgb(r, g, b)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Please pass in a valid RGB code!", ephemeral=True
            )

        role_owner = interaction.user
        created_role = await interaction.guild.create_role(
            name=name,
            reason="Member Request",
            color=valid_color,
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO custom_role (role_id, owner_discord_id) VALUES ($1, $2)',
                created_role.id,
                role_owner.id,
            )

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(config.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

        # TODO
        # add created role data on memory so it can be used later

        embed = discord.Embed(
            color=valid_color, description=f'✅ Successfully created role: **{created_role.name}**.'
        )
        embed.add_field(
            name="What to do next?",
            value=(
                "- Use `/warnet-color list` to check list of all available custom roles\n"
                "- Use `/warnet-color set` to use your created role, or\n"
                "- Ask Admin/Mod to attach custom icon on your custom role (read <#822872937161162795> for instruction), or\n"
                "- Use `/warnet-color remove` to take off your current custom role, or\n"
                "- Use `/warnet-color edit hex/rgb` to edit your created custom role"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @color_edit.command(name='hex')
    async def edit_hex_color(
        self,
        interaction: Interaction,
        new_name: str,
        hex: str,
        name: Optional[str],
        number: Optional[int],
    ) -> None:
        pass

    @color_edit.command(name='rgb')
    async def edit_rgb_color(
        self,
        interaction: Interaction,
        new_name: str,
        r: int,
        g: int,
        b: int,
        name: Optional[str],
        number: Optional[int],
    ) -> None:
        pass

    @app_commands.command(name='set')
    async def set_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @app_commands.command(name='remove')
    async def remove_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @app_commands.command(name='list')
    async def list_color(self, interaction: Interaction) -> None:
        pass

    @app_commands.command(name='info')
    async def info_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @app_commands.command(name='delete')
    async def delete_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        pass

    @app_commands.command(name='help')
    async def help_color(self, interaction: Interaction) -> None:
        pass


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Color(bot))
