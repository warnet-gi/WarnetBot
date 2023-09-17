import datetime
from typing import Optional, Union

import discord
from discord import Interaction
from discord.ext import commands

from bot.cogs.ext.tcg.utils import (
    send_user_not_registered_error_embed,
    send_user_is_not_in_guild_error_embed,
)
from bot.cogs.views.tcg import LeaderboardPagination


async def register(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    author_id = interaction.user.id
    embed: discord.Embed
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval(
            "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", author_id
        )
        if not res:
            await conn.execute("INSERT INTO tcg_leaderboard(discord_id) VALUES ($1);", author_id)
            embed = discord.Embed(
                color=discord.Colour.green(),
                title='✅ Registered successfully',
                description=f"Sekarang kamu sudah terdaftar di database TCG WARNET dan rating ELO milikmu sudah diatur menjadi 1500 by default.",
                timestamp=datetime.datetime.now(),
            )
        else:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title='❌ You are already registered',
                description="Akun kamu sudah terdaftar. Tidak perlu mendaftar lagi.",
                timestamp=datetime.datetime.now(),
            )

    await interaction.followup.send(embed=embed, ephemeral=True)


async def member_stats(
    self: commands.Cog,
    interaction: Interaction,
    member: Optional[Union[discord.Member, discord.User]],
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    user = interaction.user if not member else member
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval(
            "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", user.id
        )
        if not res:
            await send_user_not_registered_error_embed(interaction, user.id)

        else:
            records = await conn.fetch(
                "SELECT * FROM tcg_leaderboard WHERE discord_id = $1;", user.id
            )
            data = dict(records[0])

            win_count = data['win_count']
            loss_count = data['loss_count']
            elo = data['elo']
            user_tcg_title_role = (
                user.get_role(data['title']) if data['title'] is not None else None
            )
            match_played = win_count + loss_count
            win_rate = 0 if match_played == 0 else (win_count / match_played) * 100

            embed = discord.Embed(
                color=user.color,
                title=f"{user.name}'s TCG Stats",
                timestamp=datetime.datetime.now(),
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name=f"Total Win", value=f"🏆 {win_count}", inline=False)
            embed.add_field(name=f"Total Loss", value=f"❌ {loss_count}", inline=False)
            embed.add_field(name=f"Win Rate", value=f"⚖️ {win_rate:.2f}%", inline=False)
            embed.add_field(name=f"Elo Rating", value=f"⭐ {elo:.1f}", inline=False)
            embed.add_field(
                name=f"TCG Title",
                value=f"🎖️ {'No TCG title' if not user_tcg_title_role else user_tcg_title_role.mention}",
                inline=False,
            )

            await interaction.followup.send(embed=embed)


async def leaderboard(self, interaction: Interaction) -> None:
    await interaction.response.defer()

    async with self.db_pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT * FROM tcg_leaderboard WHERE win_count + loss_count > 0 ORDER BY elo DESC;"
        )
        all_records = [dict(row) for row in records]

    view = LeaderboardPagination(leaderboard_data=all_records)
    await view.start(interaction)
