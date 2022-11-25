import datetime

import discord
from discord import Interaction

from bot.config import config


async def send_missing_permission_error_embed(interaction: Interaction) -> None:
    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ You don't have permission",
        description=f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini. Cobalah untuk mengontak mereka apabila ingin melakukan claim achievement.",
        timestamp=datetime.datetime.now(),
    )

    await interaction.followup.send(embed=embed)


async def send_user_not_registered_error_embed(interaction: Interaction, member_id: int) -> None:
    embed = discord.Embed(
        color=discord.Colour.red(),
        title='❌ User not registered',
        description=f"<@{member_id}> belum terdaftar di database. Silakan <@{member_id}> untuk mendaftar terlebih dahulu menggunakan </achievement-member-register:0>",
        timestamp=datetime.datetime.now()
    )

    await interaction.followup.send(embed=embed)