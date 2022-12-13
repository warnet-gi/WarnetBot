import datetime
from typing import Optional

import discord
from discord import Interaction
from discord.ext import commands

from bot.config import config
from bot.cogs.ext.tcg.utils import (
    send_user_not_registered_error_embed,
    get_tcg_title_role,
)

async def register(self: commands.Cog, interaction:Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    author_id = interaction.user.id
    embed: discord.Embed
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", author_id)
        if res == None:
            await conn.execute("INSERT INTO tcg_leaderboard(discord_id) VALUES ($1);", author_id)
            embed = discord.Embed(
                color=discord.Colour.green(),
                title='✅ Registered successfully',
                description=f"Sekarang kamu sudah terdaftar di database TCG WARNET dan rating ELO milikmu sudah diatur menjadi 1200 by default.",
                timestamp=datetime.datetime.now()
            )
        else:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title='❌ You are already registered',
                description="Akun kamu sudah terdaftar. Tidak perlu mendaftar lagi.",
                timestamp=datetime.datetime.now()
            )

    await interaction.followup.send(embed=embed, ephemeral=True)

async def member_stats(self: commands.Cog, interaction:Interaction, member: Optional[discord.Member]) -> None:
    await interaction.response.defer()

    user = interaction.user if member == None else member
    user_id = user.id
    user_name = user.name
    user_color = user.color
    user_display_avatar_url = user.display_avatar.url
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", user_id)
        if res == None:
            await send_user_not_registered_error_embed(interaction, user_id)

        else:
            records = await conn.fetch("SELECT * FROM tcg_leaderboard WHERE discord_id = $1;", user_id)
            data = dict(records[0])

            win_count = data['win_count']
            loss_count = data['loss_count']
            elo = data['elo']
            match_played = win_count + loss_count
            win_rate = 0 if match_played == 0 else (win_count / match_played) * 100
            user_tcg_title_role = get_tcg_title_role(user)

            embed = discord.Embed(
                color=user_color,
                title=f"{user_name}'s TCG Stats",
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=user_display_avatar_url)
            embed.add_field(
                name=f"Total Win",
                value=f"🏆 {win_count}",
                inline=False
            )
            embed.add_field(
                name=f"Total Loss",
                value=f"❌ {loss_count}",
                inline=False
            )
            embed.add_field(
                name=f"Win Rate",
                value=f"⚖️ {win_rate:.2f}%",
                inline=False
            )
            embed.add_field(
                name=f"Elo Rating",
                value=f"⭐ {elo:.1f}",
                inline=False
            )
            embed.add_field(
                name=f"TCG Title",
                value=f"🎖️ {'No TCG title' if user_tcg_title_role == None else user_tcg_title_role.mention}",
                inline=False
            )

            await interaction.followup.send(embed=embed)

