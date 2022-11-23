import datetime

import Paginator
import discord
from discord import Interaction
from discord.ext import commands

from bot.config import config


async def register(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    author_id = interaction.user.id
    embed: discord.Embed
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", author_id)
        if res == None:
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

async def show_achievement_stats(self: commands.Cog, interaction: Interaction) -> None:
    await interaction.response.defer()

    author_id = interaction.user.id
    author_name = interaction.user.name
    author_color = interaction.user.color 
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", author_id)
        if res == None:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title='❌ User not registered',
                description=f"<@{author_id}> belum terdaftar di database. Silakan <@{author_id}> untuk mendaftar terlebih dahulu menggunakan </achievement-member-register:0>",
                timestamp=datetime.datetime.now()
            )

            await interaction.followup.send(embed=embed)

        else:
            total_completed = await conn.fetchval("SELECT COUNT(*) FROM achievement_progress WHERE discord_id = $1;", author_id)
            records = await conn.fetch("SELECT achievement_id FROM achievement_progress WHERE discord_id = $1 ORDER BY achievement_id ASC;", author_id)
            completed_achievement_list = [dict(row)['achievement_id'] for row in records]  # [1, 2, 3]

            # TODO: shows total completed, shows list of completed achievement (use pagination)
            stats_percentage = (total_completed / len(self.achievement_data)) * 100
            badge_id = self.get_achievement_badge_id(total_completed) 
            embed = discord.Embed(
                color=author_color,
                title=f"🏆 {author_name}'s Achievement Progress",
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(
                name=f"{author_name} has completed {stats_percentage:.2f}% of total achievements in WARNET",
                value=f"**{total_completed}**✅ of {len(self.achievement_data)} achievements",
                inline=False
            )
            embed.add_field(
                name="Current Badge",
                value="No Badge" if badge_id == None else f"<@&{badge_id}>",
                inline=False
            )


            await interaction.followup.send(embed=embed)