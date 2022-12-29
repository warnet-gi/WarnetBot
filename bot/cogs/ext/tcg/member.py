import datetime
from typing import Optional, Union

import discord
from discord import Interaction
from discord.ext import commands

from bot.config import config
from bot.cogs.ext.tcg.utils import (
    send_user_not_registered_error_embed,
    send_user_is_not_in_guild_error_embed
)

async def register(self: commands.Cog, interaction:Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    author_id = interaction.user.id
    embed: discord.Embed
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", author_id)
        if res is None:
            await conn.execute("INSERT INTO tcg_leaderboard(discord_id) VALUES ($1);", author_id)
            embed = discord.Embed(
                color=discord.Colour.green(),
                title='✅ Registered successfully',
                description=f"Sekarang kamu sudah terdaftar di database TCG WARNET dan rating ELO milikmu sudah diatur menjadi 1500 by default.",
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

async def member_stats(self: commands.Cog, interaction:Interaction, member: Optional[Union[discord.Member, discord.User]]) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    user = interaction.user if member is None else member
    user_id = user.id
    user_name = user.name
    user_color = user.color
    user_display_avatar_url = user.display_avatar.url
    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", user_id)
        if res is None:
            await send_user_not_registered_error_embed(interaction, user_id)

        else:
            records = await conn.fetch("SELECT * FROM tcg_leaderboard WHERE discord_id = $1;", user_id)
            data = dict(records[0])

            win_count = data['win_count']
            loss_count = data['loss_count']
            elo = data['elo']
            user_tcg_title_role = member.get_role(data['title']) if data['title'] is not None else None
            match_played = win_count + loss_count
            win_rate = 0 if match_played == 0 else (win_count / match_played) * 100

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
                value=f"🎖️ {'No TCG title' if user_tcg_title_role is None else user_tcg_title_role.mention}",
                inline=False
            )

            await interaction.followup.send(embed=embed)

async def leaderboard(self, interaction: Interaction) -> None:
    await interaction.response.defer()

    author = interaction.user

    async with self.db_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM tcg_leaderboard WHERE win_count + loss_count > 0 ORDER BY elo DESC;")
        all_records = [dict(row) for row in records]

        # Pick only top N
        TOP_N = 40
        all_member_data_list = [all_records[:TOP_N//2], all_records[TOP_N//2:TOP_N]]

        embed = discord.Embed(
            color=discord.Color.gold(),
            title='WARNET TCG ELO RATING LEADERBOARD',
            description='**Berikut TOP 40 ELO tertinggi di server WARNET**',
        )
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/929746553944551424/1052431858371133460/Paimon_TCG.png')
        
        if len(all_member_data_list[0]) == 0:
            embed.add_field(name='Rank  |  Player  |  W/L  |  ELO', value='**NO PLAYER IN THIS LEADERBOARD YET**')

        else:
            title_emoji = config.TCGConfig.TCG_TITLE_EMOJI
            rank_count = 1
            author_rank = 0

            for member_data_list in all_member_data_list:
                if member_data_list == all_member_data_list[1] and len(all_member_data_list[1]) == 0: continue
                
                field_value = ''
                field_name = 'Rank  |  Player  |  W/L  |  ELO' if member_data_list == all_member_data_list[0] else '|'
                for member_data in member_data_list:
                    member = interaction.guild.get_member(member_data['discord_id'])
                    # Prevent none object if user leaves but they still in the leaderboard
                    if member is None:
                        member = await self.bot.fetch_user(member_data['discord_id'])
                    
                    if len(member.name) > 10:
                        member_name = member.name[:7]+'...'
                    else:
                        member_name = member.name

                    member_title_emoji = title_emoji[member_data['title']] if member_data['title'] is not None else ''
                    row_string = f"`{rank_count:>2}` {member_title_emoji:<1} {member_name:<10} ({member_data['win_count']:>2}/{member_data['loss_count']:<2}) **{member_data['elo']:.1f}**\n"
                    field_value += row_string

                    if member.id == author.id:
                        author_rank = rank_count

                    rank_count += 1
                
                embed.add_field(name=field_name, value=field_value)

            if author_rank:
                embed.set_footer(text=f'{len(member_data_list)} members has been listed in this leaderboard. You are in rank #{author_rank}.')
            else:
                embed.set_footer(
                    text=f'{len(member_data_list)} members has been listed in this leaderboard. You are not in the leaderboard yet. ' + \
                        'Register and play at least 1 official TCG WARNET Tournament match to enter the leaderboard.'
                )

        await interaction.followup.send(embed=embed)