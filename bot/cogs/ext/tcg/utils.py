import datetime
from typing import Optional, List

import discord
from discord import Interaction

from bot.config import config


async def send_user_not_registered_error_embed(
    interaction: Interaction, member1_id: int, member2_id: Optional[int] = None
) -> None:
    desc_msg: str
    if member2_id is not None:
        desc_msg = f"<@{member1_id}> dan <@{member2_id}> belum terdaftar di database. Silakan untuk mendaftar terlebih dahulu menggunakan `/warnet-tcg register`"
    else:
        desc_msg = f"<@{member1_id}> belum terdaftar di database. Silakan <@{member1_id}> untuk mendaftar terlebih dahulu menggunakan `/warnet-tcg register`"

    embed = discord.Embed(
        color=discord.Colour.red(),
        title='❌ User not registered',
        description=desc_msg,
        timestamp=datetime.datetime.now(),
    )

    await interaction.followup.send(embed=embed)


async def send_missing_permission_error_embed(
    interaction: Interaction, custom_description: str = None
) -> None:
    description = f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini."
    if custom_description:
        description = custom_description

    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ You don't have permission",
        description=description,
        timestamp=datetime.datetime.now(),
    )

    await interaction.followup.send(embed=embed)


async def send_user_is_not_in_guild_error_embed(
    interaction: Interaction, user: discord.User
) -> None:
    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ User is not found",
        description=f"Can't find user with id `{user.id}` in this server",
    )

    await interaction.followup.send(embed=embed)


def calculate_elo(rating_winner: float, rating_loser: float) -> float:
    k_factor = 40
    score = 1  # consider as win
    diff = rating_loser - rating_winner
    ratio = diff / 400
    expected_score = 1 / (1 + 10**ratio)

    return round(k_factor * (score - expected_score), 1)


async def change_tcg_title_role(
    interaction: Interaction,
    member: discord.Member,
    current_tcg_role: Optional[discord.Role],
    current_elo: float,
) -> Optional[discord.Role]:
    target_role = check_for_eligible_tcg_title(interaction, current_elo)

    if target_role != current_tcg_role:
        if current_tcg_role:
            await member.remove_roles(current_tcg_role)

        if target_role:
            await member.add_roles(target_role, reason="Achieve new title in TCG")

            notify_embed = discord.Embed(
                color=member.color,
                description=f"⭐ {member.mention} telah mendapatkan gelar TCG baru: {target_role.mention}",
                timestamp=datetime.datetime.now(),
            )
            await interaction.channel.send(content=f"{member.mention}", embed=notify_embed)

    return target_role


def check_for_eligible_tcg_title(
    interaction: Interaction, elo_rating: float
) -> Optional[discord.Role]:
    """
    return current tcg title role id and previous role id based on total ELO rating.

    * Novice Duelist   = 1550
    * Expert Duelist   = 1600
    * Master Duelist   = 1650
    * Immortal Duelist = 1700
    """
    TCG_TITLE_ROLE_LIST = [
        interaction.guild.get_role(role_id) for role_id in config.TCGConfig.TCG_TITLE_ROLE_ID
    ]

    if elo_rating < 1550:
        return None
    elif elo_rating < 1600:
        return TCG_TITLE_ROLE_LIST[0]
    elif elo_rating < 1650:
        return TCG_TITLE_ROLE_LIST[1]
    elif elo_rating < 1700:
        return TCG_TITLE_ROLE_LIST[2]
    else:
        return TCG_TITLE_ROLE_LIST[3]
