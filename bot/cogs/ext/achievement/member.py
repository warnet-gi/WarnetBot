import datetime
from typing import Optional

import Paginator
import discord
from discord import Interaction
from discord.ext import commands

from bot.config import config
from bot.cogs.views.achievement import StatsProgressDetail
from bot.cogs.ext.achievement.utils import send_user_not_registered_error_embed


async def register(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    author_id = interaction.user.id
    embed: discord.Embed
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", author_id)
        if res is None:
            await conn.execute("INSERT INTO warnet_user(discord_id) VALUES ($1);", author_id)
            embed = discord.Embed(
                color=discord.Colour.green(),
                title='✅ Registered successfully',
                description=f"""
                Sekarang kamu sudah bisa melakukan proses claim achievement dan cek progress di </achievement-stats:0>.
                Hubungi <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> untuk claim achievement.
                """,
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


async def show_achievement_list(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer()
    await Paginator.Simple().start(interaction, pages=self.achievement_embeds)


async def show_achievement_detail(self: commands.Cog, interaction: Interaction, achievement_id: int) -> None:
    await interaction.response.defer()
        
    try:
        target_data = self.achievement_data[str(achievement_id)]

    # Handle undefined key
    except KeyError:
        error_embed = discord.Embed(
            color=discord.Colour.red(),
            title='❌ Achievement not found',
            description='Cobalah untuk memeriksa apakah id yang diinput sudah benar. Ketik </achievement-list:0> untuk melihat daftar achievement yang tersedia.',
            timestamp=datetime.datetime.now(),
        )
        await interaction.followup.send(embed=error_embed)
        return
    
    name = target_data['name']
    desc = target_data['desc']
    claim = target_data['claim']

    author_color = interaction.user.color
    embed = discord.Embed(
        color=author_color,
        title=f'🏅 {name}',
        description=desc,
        timestamp=datetime.datetime.now(),
    )
    embed.add_field(
        name="How to claim?",
        value=f"{claim}.\nHubungi <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> untuk claim achievement."
    )
    embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/761684443915485184/956797958651805716/paimon_win.gif')
    
    await interaction.followup.send(embed=embed)


async def show_achievement_stats(self: commands.Cog, interaction: Interaction, member: Optional[discord.Member]) -> None:
    await interaction.response.defer()

    user_id = interaction.user.id if member is None else member.id
    user_name = interaction.user.name if member is None else member.name
    user_color = interaction.user.color if member is None else member.color
    user_display_avatar_url = interaction.user.display_avatar.url if member is None else member.display_avatar.url
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", user_id)
        if res is None:
            await send_user_not_registered_error_embed(interaction, user_id)

        else:
            total_completed = await conn.fetchval("SELECT COUNT(*) FROM achievement_progress WHERE discord_id = $1;", user_id)
            records = await conn.fetch("SELECT achievement_id FROM achievement_progress WHERE discord_id = $1 ORDER BY achievement_id ASC;", user_id)
            completed_achievement_list = [dict(row)['achievement_id'] for row in records]  # [1, 2, 3]

            stats_percentage = (total_completed / len(self.achievement_data)) * 100
            badge_id, _ = self.get_achievement_badge_id(total_completed) 
            embed = discord.Embed(
                color=user_color,
                title=f"🏆 {user_name}'s Achievement Progress",
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=user_display_avatar_url)
            embed.add_field(
                name=f"Total completed achievement",
                value=f"✅ **{total_completed}** of {len(self.achievement_data)} achievements ({stats_percentage:.2f}%)",
                inline=False
            )
            embed.add_field(
                name="Current Badge",
                value="No Badge" if badge_id is None else f"<@&{badge_id}>",
                inline=False
            )

            view = StatsProgressDetail(
                InitialEmbed=embed,
                completed_achievement_list=completed_achievement_list,
                Member=member,
                achievement_data=self.achievement_data
            )
            await view.start(interaction)


async def show_achievement_leaderboard(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer()

    # TODO: Leaderboard shows top 30 only
