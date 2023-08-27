from datetime import datetime
from typing import Optional

import discord
from discord import Interaction, app_commands, Color as DiscordColor
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.ext.color.utils import check_role_by_name_or_number
from bot.config import config


@commands.guild_only()
class Color(commands.GroupCog, group_name='warnet-color'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.custom_role_data: dict[int, int] = {}

    color_add = app_commands.Group(name='add', description='Sub command to handle role creation.')
    color_edit = app_commands.Group(name='edit', description='Sub command to handle role editing.')

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM custom_role ORDER BY created_at ASC;")
            data_list = [dict(row) for row in records]

        for data in data_list:
            self.custom_role_data[data['role_id']] = data['owner_discord_id']
        self.custom_role_data_list = list(self.custom_role_data.keys())

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

        self.custom_role_data[created_role.id] = role_owner.id
        self.custom_role_data_list = list(self.custom_role_data.keys())

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(config.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

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

        self.custom_role_data[created_role.id] = role_owner.id
        self.custom_role_data_list = list(self.custom_role_data.keys())

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(config.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

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
        # TODO
        # Only owner can edit the role

        try:
            hex = '#' + hex if not hex.startswith('#') else hex
            valid_color = DiscordColor.from_str(hex)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Please pass in a valid HEX code!\n\nExample: `#FFF456` or `FFF456`",
                ephemeral=True,
            )

        valid, role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if valid:
            edited_role = await role_target.edit(name=new_name, color=valid_color)

            embed = discord.Embed(
                title="Custom role edited!",
                timestamp=datetime.now(),
                color=edited_role.color,
            )
            embed.add_field(
                name="New custom role settings:",
                value=(
                    f"- **Name:** {edited_role.name}\n"
                    f"- **R:** {edited_role.color.r}\n"
                    f"- **G:** {edited_role.color.g}\n"
                    f"- **B:** {edited_role.color.b}\n"
                    f"- **HEX:** {str(edited_role.color)}\n"
                ),
            )
            return await interaction.response.send_message(embed=embed)

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
        # TODO
        # Only owner can edit the role

        try:
            valid_color = DiscordColor.from_rgb(r, g, b)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Please pass in a valid RGB code!", ephemeral=True
            )

        valid, role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if valid:
            edited_role = await role_target.edit(name=new_name, color=valid_color)

            embed = discord.Embed(
                title="Custom role edited!",
                timestamp=datetime.now(),
                color=edited_role.color,
            )
            embed.add_field(
                name="New custom role settings:",
                value=(
                    f"- **Name:** {edited_role.name}\n"
                    f"- **R:** {edited_role.color.r}\n"
                    f"- **G:** {edited_role.color.g}\n"
                    f"- **B:** {edited_role.color.b}\n"
                    f"- **HEX:** {str(edited_role.color)}\n"
                ),
            )
            return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='set')
    async def set_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        # TODO
        # Check if user is using another custom role
        
        valid, role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if valid:
            user = interaction.user
            await user.add_roles(role_target)

            embed = discord.Embed(
                description=f"{user.mention} your color is now **{role_target.name}**.",
                color=role_target.color,
            )
            return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='remove')
    async def remove_color(self, interaction: Interaction) -> None:
        pass

    @app_commands.command(name='list')
    async def list_color(self, interaction: Interaction) -> None:
        pass

    @app_commands.command(name='info')
    async def info_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        valid, role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if valid:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetchrow(
                    "SELECT owner_discord_id, created_at FROM custom_role WHERE role_id=$1;",
                    role_target.id,
                )

            create_time: datetime = res['created_at']
            owner = interaction.guild.get_member(res['owner_discord_id'])

            embed = discord.Embed(
                title="Color info",
                description=(
                    f"**Owner**: {owner.name} ({owner.mention})\n"
                    f"**RGB**: {role_target.color.to_rgb()}\n"
                    f"**HEX**: {str(role_target.color)}\n"
                    f"**Created date**: {create_time.strftime('%A, %d-%m-%Y %H:%M:%S')}"
                ),
                color=role_target.color,
                timestamp=datetime.now(),
            )
            return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='delete')
    async def delete_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        # TODO allow role owner to delete their own custom role

        if interaction.user.guild_permissions.manage_roles:
            if name and number:
                await interaction.response.send_message(
                    "❌ Please use just `name` or just `number`. Not both!", ephemeral=True
                )

            elif name or number:
                found = False
                if name:
                    role_target = discord.utils.find(
                        lambda r: r.name == name, interaction.guild.roles
                    )
                    if role_target:
                        if self.custom_role_data.get(role_target.id, None):
                            found = True
                            async with self.db_pool.acquire() as conn:
                                await conn.execute(
                                    "DELETE FROM custom_role WHERE role_id = $1;", role_target.id
                                )
                            self.custom_role_data.pop(role_target.id)
                            self.custom_role_data_list = list(self.custom_role_data.keys())
                            await role_target.delete()

                elif number:
                    try:
                        # color list index is not zero-based
                        role_target_id = self.custom_role_data_list[number - 1]
                        role_target = interaction.guild.get_role(role_target_id)

                        found = True
                        async with self.db_pool.acquire() as conn:
                            await conn.execute(
                                "DELETE FROM custom_role WHERE role_id = $1;", role_target_id
                            )
                        self.custom_role_data.pop(role_target_id)
                        self.custom_role_data_list = list(self.custom_role_data.keys())
                        await role_target.delete()

                    except IndexError:
                        found = False

                if found:
                    embed = discord.Embed(
                        title="Deleted color!",
                        description=f"Successfully deleted **{role_target.name}** from the list.",
                        timestamp=datetime.now(),
                        color=role_target.color,
                    )
                    await interaction.response.send_message(embed=embed)

                else:
                    await interaction.response.send_message(
                        "❌ Failed to find the color!\nPlease use `/warnet-color list` to see all the available colors.",
                        ephemeral=True,
                    )

            else:
                await interaction.response.send_message(
                    "❌ Please supply a color `name` or a color `number`!", ephemeral=True
                )

        else:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command", ephemeral=True
            )

    @app_commands.command(name='help')
    async def help_color(self, interaction: Interaction) -> None:
        pass


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Color(bot))
