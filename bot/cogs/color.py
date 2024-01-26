import logging
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.ext.color.utils import (
    check_role_by_name_or_number,
    generate_image_color_list,
    get_current_custom_role_on_user,
    no_permission_alert,
)
from bot.config import CustomRoleConfig

logger = logging.getLogger(__name__)


@commands.guild_only()
class Color(commands.GroupCog, group_name='warnet-color'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.custom_role_data: dict[int, int] = {}  # {role_id: owner_discord_id}
        self.cache = {}

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

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        guild = before.guild
        BOOSTER_ROLE = guild.get_role(CustomRoleConfig.BOOSTER_ROLE_ID)
        roles_before = set(before.roles)
        roles_after = set(after.roles)

        # skip if no role updates on member
        if not (roles_before ^ roles_after):
            return None

        # Check if a member removed or lost their booster status
        if BOOSTER_ROLE in roles_before and BOOSTER_ROLE not in roles_after:
            role_being_used = get_current_custom_role_on_user(self, after.guild, after)
            if role_being_used:
                await after.remove_roles(role_being_used, reason="Lose Booster Status")

                embed = discord.Embed(
                    color=discord.Color.orange(),
                    title="Booster member update",
                    description=(
                        f"Removed role **{role_being_used.name}** from **{before.mention}**"
                        f"`({before.id})` due to lost their booster status."
                    ),
                )
                await guild.get_channel(CustomRoleConfig.BOOSTER_LOG_CHANNEL_ID).send(embed=embed)

    @color_add.command(
        name='hex', description='Add a color to the color list using HEX color value.'
    )
    @app_commands.describe(
        name='The name of the color role you want to create.',
        hex='The HEX color value of the new color role.',
    )
    async def add_hex_color(self, interaction: Interaction, name: str, hex: str) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        if len(self.custom_role_data_list) == CustomRoleConfig.CUSTOM_ROLE_LIMIT:
            return await interaction.followup.send(
                "❌ Maximum custom role limit has been reached. You can't create any new custom role."
            )

        try:
            hex = '#' + hex if not hex.startswith('#') else hex
            valid_color = discord.Color.from_str(hex)
        except ValueError:
            return await interaction.followup.send(
                "❌ Please pass in a valid HEX code!\n\nExample: `#FFF456` or `FFF456`",
                ephemeral=True,
            )

        role_owner = interaction.user
        created_role = await interaction.guild.create_role(
            name=name,
            reason="Member Request",
            color=valid_color,
        )
        logger.info(f'NEW ROLE HAS BEEN CREATED SUCCESSFULLY. ROLE ID: {created_role.id}')

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO custom_role (role_id, owner_discord_id) VALUES ($1, $2)',
                created_role.id,
                role_owner.id,
            )

        self.custom_role_data[created_role.id] = role_owner.id
        self.custom_role_data_list = list(self.custom_role_data.keys())

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(CustomRoleConfig.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

        self.cache['color-list'] = None

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

        await interaction.followup.send(embed=embed)

    @color_add.command(
        name='rgb', description='Add a color to the color list using RBG color value.'
    )
    @app_commands.describe(
        name='The name of the color role you want to create.',
        r='The red value of the color. (0-255)',
        g='The green value of the color. (0-255)',
        b='The blue value of the color. (0-255)',
    )
    async def add_rgb_color(
        self,
        interaction: Interaction,
        name: str,
        r: app_commands.Range[int, 0, 255],
        g: app_commands.Range[int, 0, 255],
        b: app_commands.Range[int, 0, 255],
    ) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        if len(self.custom_role_data_list) == CustomRoleConfig.CUSTOM_ROLE_LIMIT:
            return await interaction.followup.send(
                "❌ Maximum custom role limit has been reached. You can't create any new custom role."
            )

        try:
            valid_color = discord.Color.from_rgb(r, g, b)
        except ValueError:
            return await interaction.followup.send(
                "❌ Please pass in a valid RGB code!", ephemeral=True
            )

        role_owner = interaction.user
        created_role = await interaction.guild.create_role(
            name=name,
            reason="Member Request",
            color=valid_color,
        )
        logger.info(f'NEW ROLE HAS BEEN CREATED SUCCESSFULLY. ROLE ID: {created_role.id}')

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO custom_role (role_id, owner_discord_id) VALUES ($1, $2)',
                created_role.id,
                role_owner.id,
            )

        self.custom_role_data[created_role.id] = role_owner.id
        self.custom_role_data_list = list(self.custom_role_data.keys())

        # Put recent created role under boundary role
        boundary_role = interaction.guild.get_role(CustomRoleConfig.BOUNDARY_ROLE_ID)
        await created_role.edit(position=boundary_role.position - 1)

        self.cache['color-list'] = None

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

        await interaction.followup.send(embed=embed)

    @color_edit.command(
        name='hex', description='Edit a color role with a new name and new HEX color.'
    )
    @app_commands.describe(
        new_name='The new name of the color role.',
        hex='The HEX color value of the new color.',
        name='The name of the color role you want to edit. Required if "number" is empty.',
        number='The number of the color role you want to edit. Required if "name" is empty.',
    )
    async def edit_hex_color(
        self,
        interaction: Interaction,
        new_name: str,
        hex: str,
        name: Optional[str],
        number: Optional[int],
    ) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        try:
            hex = '#' + hex if not hex.startswith('#') else hex
            valid_color = discord.Color.from_str(hex)
        except ValueError:
            return await interaction.followup.send(
                "❌ Please pass in a valid HEX code!\n\nExample: `#FFF456` or `FFF456`",
                ephemeral=True,
            )

        role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if role_target:
            if (
                interaction.user.guild_permissions.manage_roles
                or interaction.user.id == self.custom_role_data[role_target.id]
            ):
                edited_role = await role_target.edit(name=new_name, color=valid_color)

                self.cache['color-list'] = None

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
                return await interaction.followup.send(embed=embed)

            else:
                return await interaction.followup.send(
                    "❌ You don't have permission to use this command", ephemeral=True
                )

    @color_edit.command(
        name='rgb', description='Edit a color role with a new name and new RGB color.'
    )
    @app_commands.describe(
        new_name='The new name of the color role.',
        r='The red value of the color. (0-255)',
        g='The green value of the color. (0-255)',
        b='The blue value of the color. (0-255)',
        name='The name of the color role you want to edit. Required if "number" is empty.',
        number='The number of the color role you want to edit. Required if "name" is empty.',
    )
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
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        try:
            valid_color = discord.Color.from_rgb(r, g, b)
        except ValueError:
            return await interaction.followup.send(
                "❌ Please pass in a valid RGB code!", ephemeral=True
            )

        role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if role_target:
            if (
                interaction.user.guild_permissions.manage_roles
                or interaction.user.id == self.custom_role_data[role_target.id]
            ):
                edited_role = await role_target.edit(name=new_name, color=valid_color)

                self.cache['color-list'] = None

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
                return await interaction.followup.send(embed=embed)

            else:
                return await interaction.followup.send(
                    "❌ You don't have permission to use this command", ephemeral=True
                )

    @app_commands.command(name='set', description='Attach a custom role on your profile.')
    @app_commands.describe(
        name='The name of the color role you want to use. Required if "number" is empty.',
        number='The number of the color role you want to use. Required if "name" is empty.',
    )
    async def set_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if role_target:
            member = interaction.user
            role_being_used = get_current_custom_role_on_user(self, interaction.guild, member)
            if role_being_used:
                await member.remove_roles(role_being_used)

            await member.add_roles(role_target)

            embed = discord.Embed(
                description=f"{member.mention} your color is now **{role_target.name}**.",
                color=role_target.color,
            )
            return await interaction.followup.send(embed=embed)

    @app_commands.command(name='remove', description='Remove your current custom role.')
    async def remove_color(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        member = interaction.user
        role_being_used = get_current_custom_role_on_user(self, interaction.guild, member)
        if role_being_used:
            await member.remove_roles(role_being_used)
            embed = discord.Embed(
                description=f"{member.mention} successfully removed **{role_being_used.name}** from your profile.",
                color=discord.Color.dark_embed(),
            )
            return await interaction.followup.send(embed=embed)

        embed = discord.Embed(
            description=f"❌ Failed to remove your color role.\nYou don't have a color role.",
            color=discord.Color.brand_red(),
        )
        return await interaction.followup.send(embed=embed)

    @app_commands.command(name='list', description='Show the color list of this server.')
    async def list_color(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        role_list = []
        for i in range(len(self.custom_role_data_list)):
            if role := interaction.guild.get_role(self.custom_role_data_list[i]):
                role_list.append(role)

        if not (image_bytes := self.cache.get('color-list')):
            image_bytes = generate_image_color_list(role_list)
            self.cache['color-list'] = image_bytes

        filename = 'custom_roles_list.png'
        image_bytes.seek(0)  # Reset the position to the beginning of the BytesIO object
        file = discord.File(image_bytes, filename)
        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_image(url=f'attachment://{filename}')

        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name='info', description='Show the basic info of a custom role.')
    @app_commands.describe(
        name='The name of the color role you want to see the info. Required if "number" is empty.',
        number='The number of the color role you want to see the info. Required if "name" is empty.',
    )
    async def info_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if role_target:
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
                    f"**Role name**: {role_target.name} ({role_target.mention})\n"
                    f"**Owner**: {(owner.name + ' (' + owner.mention + ')') if owner else 'No Owner'}\n"
                    f"**RGB**: {role_target.color.to_rgb()}\n"
                    f"**HEX**: {str(role_target.color)}\n"
                    f"**Created date**: {create_time.strftime('%A, %d-%m-%Y %H:%M:%S')}"
                ),
                color=role_target.color,
                timestamp=datetime.now(),
            )
            return await interaction.followup.send(embed=embed)

    @app_commands.command(name='delete', description='Delete custom role from list and database.')
    @app_commands.describe(
        name='The name of the color role you want delete. Required if "number" is empty.',
        number='The number of the color role you want to delete. Required if "name" is empty.',
    )
    async def delete_color(
        self, interaction: Interaction, name: Optional[str], number: Optional[int]
    ) -> None:
        await interaction.response.defer()
        role_target = await check_role_by_name_or_number(self, interaction, name, number)
        if role_target:
            if (
                interaction.user.guild_permissions.manage_roles
                or interaction.user.id == self.custom_role_data[role_target.id]
            ):
                if self.custom_role_data.get(role_target.id, None):
                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "DELETE FROM custom_role WHERE role_id = $1;", role_target.id
                        )
                    self.custom_role_data.pop(role_target.id)
                    self.custom_role_data_list = list(self.custom_role_data.keys())
                    await role_target.delete()
                    logger.info(f'ROLE ID {role_target.id} IS DELETED')

                    self.cache['color-list'] = None

                    embed = discord.Embed(
                        title="Deleted color!",
                        description=f"Successfully deleted **{role_target.name}** from the list.",
                        timestamp=datetime.now(),
                        color=role_target.color,
                    )
                    return await interaction.followup.send(embed=embed)

            else:
                return await no_permission_alert(interaction)

    @app_commands.command(name='help', description='Show the list of available commands.')
    async def help_color(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        embed = discord.Embed(
            title="Color Features",
            color=discord.Color.light_embed(),
        )
        embed.add_field(
            name='/warnet-color add hex',
            value='Membuat custom role dengan warna tertentu menggunakan kode HEX.',
        )
        embed.add_field(
            name='/warnet-color add rgb',
            value='Membuat custom role dengan warna tertentu menggunakan kode RGB.',
        )
        embed.add_field(
            name='/warnet-color edit hex',
            value='Mengedit nama custom role dan mengganti warna menggunakan kode HEX.',
        )
        embed.add_field(
            name='/warnet-color edit rgb',
            value='Mengedit nama custom role dan mengganti warna menggunakan kode RGB.',
        )
        embed.add_field(
            name='/warnet-color list',
            value='Melihat daftar custom role yang tersedia.',
        )
        embed.add_field(
            name='/warnet-color set',
            value='Memasang custom role yang ada pada profile.',
        )
        embed.add_field(
            name='/warnet-color remove',
            value='Mencopot custom role yang ada pada profile.',
        )
        embed.add_field(
            name='/warnet-color info',
            value='Menampilkan informasi warna, tanggal pembuatan, dan pemilik dari custom role.',
        )
        embed.add_field(
            name='/warnet-color delete',
            value='Menghapus custom role dari database secara permanen. Membutuhkan permission `manage_roles`.',
        )
        embed.add_field(
            name='/warnet-color help',
            value='Menampilkan daftar perintah yang tersedia untuk fitur custom role.',
        )
        return await interaction.followup.send(embed=embed)

    @commands.command(name='colorsync')
    async def sync_color(self, ctx: commands.Context) -> None:
        await ctx.typing()
        if ctx.author.guild_permissions.manage_roles:
            async with self.db_pool.acquire() as conn:
                records = await conn.fetch("SELECT * FROM custom_role ORDER BY created_at ASC;")
                data_list = [dict(row) for row in records]

            self.custom_role_data = {}
            for data in data_list:
                if ctx.guild.get_role(data['role_id']):
                    self.custom_role_data[data['role_id']] = data['owner_discord_id']
            self.custom_role_data_list = list(self.custom_role_data.keys())
            logger.info(f'ROLE LIST HAS BEEN SYNCED SUCCESSFULLY')

            self.cache['color-list'] = None

            await ctx.reply("_Custom roles have been synced_", mention_author=False)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Color(bot))
