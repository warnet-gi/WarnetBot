import datetime

import discord
from discord import Interaction

from bot import config
from bot.helper import no_channel_alert, no_guild_alert


async def send_user_not_registered_error_embed(
    interaction: Interaction, member1_id: int, member2_id: int | None = None
) -> None:
    desc_msg: str
    if member2_id:
        desc_msg = f"<@{member1_id}> dan <@{member2_id}> belum terdaftar di database. Silakan untuk mendaftar terlebih dahulu menggunakan `/warnet-tcg register`"
    else:
        desc_msg = f"<@{member1_id}> belum terdaftar di database. Silakan <@{member1_id}> untuk mendaftar terlebih dahulu menggunakan `/warnet-tcg register`"

    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ User not registered",
        description=desc_msg,
        timestamp=datetime.datetime.now(tz=datetime.UTC),
    )

    await interaction.followup.send(embed=embed)


async def send_missing_permission_error_embed(
    interaction: Interaction, custom_description: str = ""
) -> None:
    description = f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini."
    if custom_description:
        description = custom_description

    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ You don't have permission",
        description=description,
        timestamp=datetime.datetime.now(tz=datetime.UTC),
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
    member: discord.Member | discord.User,
    current_tcg_role: discord.Role | None,
    current_elo: float,
) -> discord.Role | None:
    target_role = await check_for_eligible_tcg_title(interaction, current_elo)

    if target_role != current_tcg_role:
        if current_tcg_role:
            await member.remove_roles(current_tcg_role)

        if not interaction.channel:
            return await no_channel_alert(interaction=interaction)

        if target_role:
            await member.add_roles(target_role, reason="Achieve new title in TCG")

            notify_embed = discord.Embed(
                color=member.color,
                description=f"⭐ {member.mention} telah mendapatkan gelar TCG baru: {target_role.mention}",
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )
            await interaction.channel.send(
                content=f"{member.mention}", embed=notify_embed
            )

    return target_role


async def check_for_eligible_tcg_title(
    interaction: Interaction, elo_rating: float
) -> discord.Role | None:
    """
    return current tcg title role id and previous role id based on total ELO rating.

    * Novice Duelist   = 1550
    * Expert Duelist   = 1600
    * Master Duelist   = 1650
    * Immortal Duelist = 1700
    """
    if not interaction.guild:
        return await no_guild_alert(interaction=interaction)

    tcg_title_role_list = [
        interaction.guild.get_role(role_id)
        for role_id in config.TCGConfig.TCG_TITLE_ROLE_ID
    ]

    novice_duelist = 1550
    expert_duelist = 1600
    master_duelist = 1650
    immortal_duelist = 1700

    if elo_rating < novice_duelist:
        return None
    if elo_rating < expert_duelist:
        return tcg_title_role_list[0]
    if elo_rating < master_duelist:
        return tcg_title_role_list[1]
    if elo_rating < immortal_duelist:
        return tcg_title_role_list[2]
    return tcg_title_role_list[3]
