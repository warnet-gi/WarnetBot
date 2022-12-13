import datetime
from typing import Optional

import discord
from discord import Interaction

from bot.config import config


async def send_user_not_registered_error_embed(interaction: Interaction, member_id: int) -> None:
    embed = discord.Embed(
        color=discord.Colour.red(),
        title='❌ User not registered',
        description=f"<@{member_id}> belum terdaftar di database. Silakan <@{member_id}> untuk mendaftar terlebih dahulu menggunakan </tcg register:0>",
        timestamp=datetime.datetime.now()
    )

    await interaction.followup.send(embed=embed)


def get_tcg_title_role(member: discord.Member) -> Optional[discord.Role]:
    for role_id in config.TCG_TITLE_ROLE_ID:
        if member.get_role(role_id) != None:
            return member.get_role(role_id)


    return None