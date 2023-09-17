import io
from imagetext_py import Canvas, FontDB, Paint, Color, draw_text
from typing import Optional

import discord
from discord import Interaction, Role, Member
from discord.ext import commands

from bot.config.config import CustomRoleConfig


async def check_role_by_name_or_number(
    self: commands.Cog,
    interaction: Interaction,
    name: Optional[str],
    number: Optional[int],
) -> Optional[Role]:
    if name and number:
        return await interaction.response.send_message(
            "❌ Please use just `name` or just `number`. Not both!", ephemeral=True
        )

    elif name or number:
        if name:
            role_target = discord.utils.find(lambda r: r.name == name, interaction.guild.roles)
        elif number:
            try:
                role_target_id = self.custom_role_data_list[number - 1]
                role_target = interaction.guild.get_role(role_target_id)
            except IndexError:
                role_target = None

        if not role_target:
            return await interaction.response.send_message(
                "❌ Failed to find the color!\nPlease use `/warnet-color list` to see all the available colors.",
                ephemeral=True,
            )

        return role_target

    else:
        return await interaction.response.send_message(
            "❌ Please supply a color `name` or a color `number`!", ephemeral=True
        )


def get_current_custom_role_on_user(
    self: commands.Cog, guild: discord.Guild, member: Member
) -> Optional[Role]:
    member_role_id_list = [role.id for role in member.roles]
    res = set(member_role_id_list) & set(self.custom_role_data_list)

    return guild.get_role(list(res)[0]) if res else None


def generate_image_color_list(role_list: list[discord.Role]) -> io.BytesIO:
    """
    Generate an image to show the available list of custom roles.
    There are certain rows per column. Each column has 300px wide.
    """

    FontDB.LoadFromPath('Noto', CustomRoleConfig.FONT_NOTO)
    FontDB.LoadFromPath('Noto-jp', CustomRoleConfig.FONT_NOTO_JP)
    FontDB.LoadFromPath('Noto-cn', CustomRoleConfig.FONT_NOTO_CN)
    font = FontDB.Query('Noto Noto-jp Noto-cn')

    total_data = len(role_list)
    column_px = 300
    if total_data <= 15:
        boundary = 5  # max item per column
        row_px = 200
    elif total_data <= 30:
        boundary = 10
        row_px = 400
    elif total_data <= 45:
        boundary = 15
        row_px = 600
    elif total_data <= 60:
        boundary = 20
        row_px = 800
    else:
        boundary = 25
        row_px = 1000

    background_color = (0, 0, 0, 0)  # RGBA format with alpha set to 0 for transparency
    column_need = total_data // boundary + (1 if total_data % boundary else 0)
    width, height = column_px * column_need, row_px
    canvas = Canvas(width, height, background_color)

    number = 1
    for col in range(column_need):
        x_now = (col * column_px) + 10
        y_now = 1
        for role in role_list[col * boundary : (col + 1) * boundary]:
            name = role.name[:20] + '...' if len(role.name) > 20 else role.name
            text = f'{number}. {name}'
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
    image.save(image_bytes, format='PNG')

    return image_bytes
