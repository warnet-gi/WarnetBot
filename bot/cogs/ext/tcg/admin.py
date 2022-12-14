import datetime
from typing import Optional

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.cogs.views.general import Confirm
from bot.config import config
from bot.cogs.ext.tcg.utils import (
    send_user_not_registered_error_embed,
    send_missing_permission_error_embed,
    calculate_elo,
    change_tcg_title_role
) 


async def reset_member_stats(self, interaction: Interaction, member: discord.Member) -> None:
    await interaction.response.defer()

    user_id = member.id
    if interaction.user.guild_permissions.administrator:
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", user_id)
            if res == None:
                await send_user_not_registered_error_embed(interaction, user_id)

            else:
                embed = discord.Embed(
                    color=discord.Colour.yellow(),
                    description=f"Yakin akan mereset ulang progress dari user {member.mention}?"
                )
                view = Confirm()
                msg: discord.Message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                await view.wait()

                if view.value == None:
                    await msg.edit(content='**Time Out**', embed=None, view=None)
                
                elif view.value:
                    await conn.execute(
                        """
                        UPDATE tcg_leaderboard
                        SET win_count=0, loss_count=0, elo=1500, title=NULL
                        WHERE discord_id = $1;
                        """,
                        user_id
                    )
                    
                    # Remove tcg title role(s) after reset
                    TCG_TITLE_ROLE_LIST = [interaction.guild.get_role(role_id) for role_id in config.TCG_TITLE_ROLE_ID]
                    await member.remove_roles(*TCG_TITLE_ROLE_LIST)

                    await msg.edit(content=f'✅ **Sukses melakukan reset progress TCG kepada {member.mention}**', embed=None, view=None)
                    
                    notify_embed = discord.Embed(
                        color= discord.Color.default(),
                        description=f"TCG stats milik {member.mention} telah direset",
                        timestamp=datetime.datetime.now(),
                    )
                    notify_embed.set_footer(text=f'Reset by {interaction.user.name}')

                    await interaction.channel.send(
                        embed=notify_embed,
                        reference=msg
                    )

                else:
                    await msg.delete()
    else:
        await send_missing_permission_error_embed(interaction)


async def reset_all_member_stats(self, interaction: Interaction) -> None:
    await interaction.response.defer()

    if interaction.user.guild_permissions.administrator:
        async with self.db_pool.acquire() as conn:
            embed = discord.Embed(
                color=discord.Colour.yellow(),
                description=f"Yakin akan mereset ulang semua progress user?"
            )
            view = Confirm()
            msg: discord.Message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            await view.wait()

            if view.value == None:
                await msg.edit(content='**Time Out**', embed=None, view=None)
            
            elif view.value:
                await msg.edit(content='<a:loading:747680523459231834> **Resetting the TCG database...**', embed=None, view=None)
                
                # Remove tcg title role after reset
                records = await conn.fetch("SELECT * FROM tcg_leaderboard;")
                member_target_list = [dict(row) for row in records]
                for member_data in member_target_list:
                    member_id = member_data['discord_id']
                    if interaction.guild.get_member(member_id):
                        member = interaction.guild.get_member(member_id)
                        if member and member_data['title']:
                            member_tcg_role = interaction.guild.get_role(member_data['title'])
                            
                            await member.remove_roles(member_tcg_role)

                await conn.execute("UPDATE tcg_leaderboard SET win_count=0, loss_count=0, elo=1500, title=NULL;")

                await msg.edit(content=f'✅ **Sukses melakukan reset progress TCG kepada semua member**', embed=None, view=None)
                
                notify_embed = discord.Embed(
                    color= discord.Color.default(),
                    description=f"Semua TCG stats telah direset",
                    timestamp=datetime.datetime.now(),
                )
                notify_embed.set_footer(text=f'Reset by {interaction.user.name}')

                await interaction.channel.send(
                    embed=notify_embed,
                    reference=msg
                )

            else:
                await msg.delete()

    else:
        await send_missing_permission_error_embed(interaction)


async def set_match_result(self, interaction: Interaction, winner: discord.Member, loser: discord.Member) -> None:
    await interaction.response.defer()


    if interaction.user.guild_permissions.administrator:
        async with self.db_pool.acquire() as conn:
            res1 = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", winner.id)
            res2 = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", loser.id)
            if res1 == None and res2 == None:
                await send_user_not_registered_error_embed(interaction, winner.id, member2_id=loser.id)
            elif res1 == None:
                await send_user_not_registered_error_embed(interaction, winner.id)
            elif res2 == None:
                await send_user_not_registered_error_embed(interaction, loser.id)
            elif winner == loser:
                await interaction.followup.send(content="Winner and Loser must be different user!")
            else:
                records = await conn.fetch("SELECT * FROM tcg_leaderboard WHERE discord_id = $1 OR discord_id = $2;", winner.id, loser.id)
                if dict(records[0])['discord_id'] == winner.id:
                    winner_data = dict(records[0])
                    loser_data = dict(records[1])
                else:
                    winner_data = dict(records[1])
                    loser_data = dict(records[0])

                elo_diff = calculate_elo(winner_data['elo'], loser_data['elo'])
                elo_after_win = winner_data['elo'] + elo_diff
                elo_after_loss = loser_data['elo'] - elo_diff

                embed = discord.Embed(
                    title='Match Result',
                    color=discord.Color.blurple(),
                )
                embed.add_field(
                    name=f"{str(winner)} VS {str(loser)}",
                    value=f"""
                    🏆 {winner.name} ({elo_after_win:.1f}) (+{elo_diff})
                    ❌ {loser.name} ({elo_after_loss:.1f}) (-{elo_diff})
                    """
                )

                await interaction.followup.send(embed=embed)

                winner_current_tcg_role = None
                loser_current_tcg_role = None
                if winner_data['title']:
                    winner_current_tcg_role = winner.get_role(winner_data['title']) 
                if loser_data['title']:
                    loser_current_tcg_role = loser.get_role(loser_data['title']) 
                
                new_tcg_role = await change_tcg_title_role(interaction, winner, winner_current_tcg_role, elo_after_win)
                await conn.execute(
                    "UPDATE tcg_leaderboard SET win_count=win_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_win,
                    new_tcg_role.id if new_tcg_role != None else None,
                    winner_data['discord_id']
                )
                
                new_tcg_role = await change_tcg_title_role(interaction, loser, loser_current_tcg_role, elo_after_loss)
                await conn.execute(
                    "UPDATE tcg_leaderboard SET loss_count=loss_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_loss,
                    new_tcg_role.id if new_tcg_role != None else None,
                    loser_data['discord_id']
                )
    
    else:
        await send_missing_permission_error_embed(interaction)

async def set_member_stats(
    self, interaction:Interaction,
    member: discord.Member,
    win_count: Optional[app_commands.Range[int, 0]],
    loss_count: Optional[app_commands.Range[int, 0]],
    elo: Optional[app_commands.Range[float, 0]]
) -> None:
    await interaction.response.defer()

    if interaction.user.guild_permissions.administrator:
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval("SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", member.id)
            if res == None:
                await send_user_not_registered_error_embed(interaction, member.id)
            
            else:
                await conn.execute(
                    f"UPDATE tcg_leaderboard SET win_count={win_count if win_count != None else 'win_count'}, " +
                    f"loss_count={loss_count if loss_count != None else 'loss_count'}, " +
                    f"elo={elo if elo != None else 'elo'}  WHERE discord_id = {member.id};"
                )

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    description=f'{member.mention} stats has been set.',
                    timestamp=datetime.datetime.now()
                )
                embed.set_footer(text=f'Set by {interaction.user.name}')
                
                await interaction.followup.send(embed=embed)
    else:
        await send_missing_permission_error_embed(interaction)