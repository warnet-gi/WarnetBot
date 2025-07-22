import io
import logging

import discord
from discord import Interaction, Member, Role, User
from discord.ext import commands
from imagetext_py import Canvas, Color, FontDB, Paint, draw_text

from bot.config import CustomRoleConfig
from bot.helper import no_guild_alert, value_is_none

logger = logging.getLogger(__name__)


async def check_role_by_name_or_number(
    self: commands.Cog,
    interaction: Interaction,
    name: str | None,
    number: int | None,
) -> Role | None:
    if not interaction.guild:
        return await no_guild_alert(interaction=interaction)

    role_target = None
    if name:
        role_target = discord.utils.find(
            lambda r: r.name == name, interaction.guild.roles
        )
    elif number:
        try:
            role_target_id = self.custom_role_data_list[number - 1]
            role_target = interaction.guild.get_role(role_target_id)
        except IndexError:
            role_target = None

    if not role_target:
        await interaction.followup.send(
            "❌ Failed to find the color!\nPlease use `/warnet-color list` to see all the available colors."
        )
        return None

    return role_target


async def move_role_to_under_boundary(interaction: Interaction, role: Role) -> None:
    if not interaction.guild:
        return await no_guild_alert(interaction=interaction)

    upper_boundary = interaction.guild.get_role(CustomRoleConfig.UPPER_BOUNDARY_ROLE_ID)
    if not upper_boundary:
        return await value_is_none(
            value=f"upper_boundary {CustomRoleConfig.UPPER_BOUNDARY_ROLE_ID}",
            interaction=interaction,
        )

    try:
        await role.move(above=upper_boundary, reason="Update custom role position")
    except discord.Forbidden:
        logger.exception(
            "Failed to move role to the bottom due to insufficient permissions.",
            extra={"role_id": role.id},
        )
        return await error_move_role(interaction, role)
    except discord.HTTPException:
        logger.exception(
            "Failed to move role to the bottom due to HTTPException",
            extra={"role_id": role.id},
        )
        return await error_move_role(interaction, role)
    except Exception:
        logger.exception(
            "An unexpected error occurred while moving role to the bottom",
            extra={"role_id": role.id},
        )
        return await error_move_role(interaction, role)
    return None


def get_current_custom_role_on_user(
    self: commands.Cog, guild: discord.Guild, member: User | Member
) -> Role | None:
    member_role_id_list = [role.id for role in member.roles]
    res = set(member_role_id_list) & set(self.custom_role_data_list)

    return guild.get_role(next(iter(res))) if res else None


def generate_image_color_list(role_list: list[discord.Role]) -> io.BytesIO:
    """
    Generate an image to show the available list of custom roles.
    There are certain rows per column. Each column has 300px wide.
    """

    FontDB.LoadFromPath("Noto", CustomRoleConfig.FONT_NOTO)
    FontDB.LoadFromPath("Noto-jp", CustomRoleConfig.FONT_NOTO_JP)
    FontDB.LoadFromPath("Noto-cn", CustomRoleConfig.FONT_NOTO_CN)
    font = FontDB.Query("Noto Noto-jp Noto-cn")

    total_data = len(role_list)
    column_px = 300
    if total_data <= 15 * 1:
        boundary = 5  # max item per column
        row_px = 200
    elif total_data <= 15 * 2:
        boundary = 10
        row_px = 400
    elif total_data <= 15 * 3:
        boundary = 15
        row_px = 600
    elif total_data <= 15 * 4:
        boundary = 20
        row_px = 800
    else:
        boundary = 25
        row_px = 1000

    background_color = Color(
        0, 0, 0, 0
    )  # RGBA format with alpha set to 0 for transparency
    column_need = total_data // boundary + (1 if total_data % boundary else 0)
    width, height = column_px * column_need, row_px
    canvas = Canvas(width, height, background_color)

    number = 1
    max_role_len = 15
    for col in range(column_need):
        x_now = (col * column_px) + 10
        y_now = 1
        for role in role_list[col * boundary : (col + 1) * boundary]:
            name = (
                role.name[:15] + "..." if len(role.name) > max_role_len else role.name
            )
            text = f"{number}. {name}"
            fill_color = Paint.Color(Color(*role.color.to_rgb()))

            draw_text(
                canvas=canvas,
                text=text,
                x=x_now,
                y=y_now,
                size=CustomRoleConfig.FONT_SIZE,
                font=font,
                draw_emojis=True,
                fill=fill_color,
            )

            y_now += CustomRoleConfig.FONT_SIZE + 10
            number += 1

    image_bytes = io.BytesIO()
    image = canvas.to_image()
    image.save(image_bytes, format="PNG")

    return image_bytes


def hex_to_discord_color(hex_color: str) -> discord.Color:
    """
    Convert a hex color string to a discord.Color object.
    """
    hex_color = "#" + hex_color if not hex_color.startswith("#") else hex_color
    return discord.Color.from_str(hex_color)


async def error_move_role(interaction: Interaction, role: Role) -> None:
    return await interaction.followup.send(
        f"❌ Failed to move the role `{role.name}`. Please contact the server administrator.",
        ephemeral=True,
    )
