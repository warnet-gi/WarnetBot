import datetime
from typing import Optional, Union

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from bot import config
from bot.cogs.ext.tcg.utils import (
    calculate_elo,
    change_tcg_title_role,
    send_missing_permission_error_embed,
    send_user_is_not_in_guild_error_embed,
    send_user_not_registered_error_embed,
)
from bot.cogs.views.general import Confirm


async def register_member(
    self, interaction: Interaction, member: Union[discord.Member, discord.User]
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        member_id = member.id
        embed: discord.Embed
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", member_id
            )
            if not res:
                await conn.execute(
                    "INSERT INTO tcg_leaderboard(discord_id) VALUES ($1);", member_id
                )
                embed = discord.Embed(
                    color=discord.Colour.green(),
                    title='✅ Registered successfully',
                    description=f"{member.mention} sudah terdaftar di database TCG WARNET dan rating ELO miliknya sudah diatur menjadi 1500 by default.",
                    timestamp=datetime.datetime.now(),
                )
            else:
                embed = discord.Embed(
                    color=discord.Colour.red(),
                    title='❌ member is already registered',
                    description=f"Akun {member.mention} sudah terdaftar. Tidak perlu didaftarkan lagi.",
                    timestamp=datetime.datetime.now(),
                )

        await interaction.followup.send(embed=embed)

    else:
        custom_description = (
            f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}>, <@&{config.ADMINISTRATOR_ROLE_ID['mod']}>, "
            + f"atau <@&{config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID}> yang bisa menggunakan command ini."
        )
        await send_missing_permission_error_embed(
            interaction, custom_description=custom_description
        )


async def unregister_member(
    self, interaction: Interaction, member: Union[discord.Member, discord.User]
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if interaction.user.guild_permissions.administrator:
        member_id = member.id
        embed: discord.Embed
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", member_id
            )
            if not res:
                embed = discord.Embed(
                    color=discord.Colour.red(),
                    title='❌ member is already not registered',
                    description=f"Akun {member.mention} tidak terdaftar sejak awal.",
                    timestamp=datetime.datetime.now(),
                )

                await interaction.followup.send(embed=embed)

            else:
                embed = discord.Embed(
                    color=discord.Colour.yellow(),
                    description=f"Yakin akan menghapus {member.mention} dari leaderboard?",
                )
                view = Confirm()
                msg: discord.Message = await interaction.followup.send(embed=embed, view=view)
                await view.wait()

                if not view.value:
                    await msg.edit(content='**Time Out**', embed=None, view=None)

                elif view.value:
                    await conn.execute(
                        "DELETE FROM tcg_leaderboard WHERE discord_id = $1;", member_id
                    )

                    await msg.edit(
                        content=f'✅ **Sukses menghapus {member.mention} dari leaderboard**',
                        embed=None,
                        view=None,
                    )

                else:
                    await msg.delete()

    else:
        await send_missing_permission_error_embed(interaction)


async def reset_member_stats(
    self, interaction: Interaction, member: Union[discord.Member, discord.User]
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    user_id = member.id
    if interaction.user.guild_permissions.administrator:
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", user_id
            )
            if not res:
                await send_user_not_registered_error_embed(interaction, user_id)

            else:
                embed = discord.Embed(
                    color=discord.Colour.yellow(),
                    description=f"Yakin akan mereset ulang progress dari user {member.mention}?",
                )
                view = Confirm()
                msg: discord.Message = await interaction.followup.send(
                    embed=embed, view=view, ephemeral=True
                )
                await view.wait()

                if not view.value:
                    await msg.edit(content='**Time Out**', embed=None, view=None)

                elif view.value:
                    await conn.execute(
                        """
                        UPDATE tcg_leaderboard
                        SET win_count=0, loss_count=0, elo=1500, title=NULL
                        WHERE discord_id = $1;
                        """,
                        user_id,
                    )

                    # Remove tcg title role(s) after reset
                    TCG_TITLE_ROLE_LIST = [
                        interaction.guild.get_role(role_id)
                        for role_id in config.TCGConfig.TCG_TITLE_ROLE_ID
                    ]
                    await member.remove_roles(*TCG_TITLE_ROLE_LIST)

                    await msg.edit(
                        content=f'✅ **Sukses melakukan reset progress TCG kepada {member.mention}**',
                        embed=None,
                        view=None,
                    )

                    notify_embed = discord.Embed(
                        color=discord.Color.default(),
                        description=f"TCG stats milik {member.mention} telah direset",
                        timestamp=datetime.datetime.now(),
                    )
                    notify_embed.set_footer(
                        text=f'Reset by {interaction.user.name}',
                        icon_url=interaction.user.display_avatar.url,
                    )

                    await interaction.channel.send(embed=notify_embed, reference=msg)

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
                description=f"Yakin akan mereset ulang semua progress user?",
            )
            view = Confirm()
            msg: discord.Message = await interaction.followup.send(
                embed=embed, view=view, ephemeral=True
            )
            await view.wait()

            if not view.value:
                await msg.edit(content='**Time Out**', embed=None, view=None)

            elif view.value:
                await msg.edit(
                    content='<a:loading:747680523459231834> **Resetting the TCG database...**',
                    embed=None,
                    view=None,
                )

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

                await conn.execute(
                    "UPDATE tcg_leaderboard SET win_count=0, loss_count=0, elo=1500, title=NULL;"
                )

                notify_embed = discord.Embed(
                    color=discord.Color.blurple(),
                    title=f"✅ Sukses melakukan reset progress TCG kepada semua member",
                    timestamp=datetime.datetime.now(),
                )
                notify_embed.set_footer(
                    text=f'Reset by {interaction.user.name}',
                    icon_url=interaction.user.display_avatar.url,
                )

                await msg.edit(content=None, embed=notify_embed, view=None)

            else:
                await msg.delete()

    else:
        await send_missing_permission_error_embed(interaction)


async def set_match_result(
    self,
    interaction: Interaction,
    winner: Union[discord.Member, discord.User],
    loser: Union[discord.Member, discord.User],
) -> None:
    await interaction.response.defer()

    if isinstance(winner, discord.User):
        winner = await self.bot.fetch_user(winner.id)
    if isinstance(loser, discord.User):
        loser = await self.bot.fetch_user(loser.id)

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        async with self.db_pool.acquire() as conn:
            res1 = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", winner.id
            )
            res2 = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", loser.id
            )
            if not res1 and not res2:
                await send_user_not_registered_error_embed(
                    interaction, winner.id, member2_id=loser.id
                )
            elif not res1:
                await send_user_not_registered_error_embed(interaction, winner.id)
            elif not res2:
                await send_user_not_registered_error_embed(interaction, loser.id)
            elif winner == loser:
                await interaction.followup.send(content="Winner and Loser must be different user!")
            else:
                records = await conn.fetch(
                    "SELECT * FROM tcg_leaderboard WHERE discord_id = $1 OR discord_id = $2;",
                    winner.id,
                    loser.id,
                )
                if dict(records[0])['discord_id'] == winner.id:
                    winner_data = dict(records[0])
                    loser_data = dict(records[1])
                else:
                    winner_data = dict(records[1])
                    loser_data = dict(records[0])

                # save the current data to history list for /undo-match-result command
                self.match_history.append([winner_data, loser_data])

                elo_diff = calculate_elo(winner_data['elo'], loser_data['elo'])
                elo_after_win = winner_data['elo'] + elo_diff
                elo_after_loss = loser_data['elo'] - elo_diff

                embed = discord.Embed(
                    title='Match Result',
                    color=discord.Color.blurple(),
                    timestamp=datetime.datetime.now(),
                )
                embed.add_field(
                    name=f"{winner.name} VS {loser.name}",
                    value=f"🏆 {winner.name} ({elo_after_win:.1f}) (+{elo_diff})\n❌ {loser.name} ({elo_after_loss:.1f}) (-{elo_diff})",
                )
                embed.set_footer(
                    text=f'Score added by {interaction.user}',
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=embed)

                # Send match log for event
                if interaction.channel_id == config.TCGConfig.TCG_MATCH_REPORT_CHANNEL_ID:
                    match_log_channel = interaction.guild.get_channel(
                        config.TCGConfig.TCG_MATCH_LOG_CHANNEL_ID
                    )
                    await match_log_channel.send(embed=embed)

                winner_current_tcg_role = None
                loser_current_tcg_role = None
                if winner_data['title']:
                    winner_current_tcg_role = winner.get_role(winner_data['title'])
                if loser_data['title']:
                    loser_current_tcg_role = loser.get_role(loser_data['title'])

                new_tcg_role = await change_tcg_title_role(
                    interaction, winner, winner_current_tcg_role, elo_after_win
                )
                await conn.execute(
                    "UPDATE tcg_leaderboard SET win_count=win_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_win,
                    new_tcg_role.id if new_tcg_role else None,
                    winner_data['discord_id'],
                )

                new_tcg_role = await change_tcg_title_role(
                    interaction, loser, loser_current_tcg_role, elo_after_loss
                )
                await conn.execute(
                    "UPDATE tcg_leaderboard SET loss_count=loss_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_loss,
                    new_tcg_role.id if new_tcg_role else None,
                    loser_data['discord_id'],
                )

    else:
        custom_description = (
            f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}>, <@&{config.ADMINISTRATOR_ROLE_ID['mod']}>, "
            + f"atau <@&{config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID}> yang bisa menggunakan command ini."
        )
        await send_missing_permission_error_embed(
            interaction, custom_description=custom_description
        )


async def undo_match_result(
    self, interaction: Interaction, member: Union[discord.Member, discord.User]
) -> None:
    await interaction.response.defer()

    match_history: list = self.match_history
    if len(match_history) == 0:
        return await interaction.followup.send(
            content=f'Match history for {member.name} is not found.'
        )

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        if isinstance(member, discord.User):
            member = await self.bot.fetch_user(member.id)

        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", member.id
            )
            if not res:
                await send_user_not_registered_error_embed(interaction, member.id)

            else:
                winner: discord.Member = None
                loser: discord.Member = None

                # Search member in match history
                idx = len(match_history) - 1
                found = False
                while idx >= 0 and not found:
                    winner_data, loser_data = match_history[idx]
                    if (
                        winner_data['discord_id'] != member.id
                        and loser_data['discord_id'] != member.id
                    ):
                        idx -= 1

                    else:
                        found = True

                        if winner_data['discord_id'] == member.id:
                            winner = member
                            loser = interaction.guild.get_member(loser_data['discord_id'])
                            if not loser:
                                await self.bot.fetch_user(loser_data['discord_id'])

                        elif loser_data['discord_id'] == member.id:
                            loser = member
                            winner = interaction.guild.get_member(winner_data['discord_id'])
                            if not winner:
                                await self.bot.fetch_user(winner_data['discord_id'])

                        await conn.execute(
                            "UPDATE tcg_leaderboard SET win_count=$1, loss_count=$2, elo=$3, title=$4 WHERE discord_id = $5;",
                            winner_data['win_count'],
                            winner_data['loss_count'],
                            winner_data['elo'],
                            winner_data['title'],
                            winner_data['discord_id'],
                        )
                        await conn.execute(
                            "UPDATE tcg_leaderboard SET win_count=$1, loss_count=$2, elo=$3, title=$4 WHERE discord_id = $5;",
                            loser_data['win_count'],
                            loser_data['loss_count'],
                            loser_data['elo'],
                            loser_data['title'],
                            loser_data['discord_id'],
                        )

                        match_history.pop(idx)

                if found:
                    embed = discord.Embed(
                        title='Match Reverted',
                        color=discord.Color.yellow(),
                        timestamp=datetime.datetime.now(),
                    )
                    embed.add_field(
                        name=f'{winner.name} VS {loser.name}',
                        value='Match has been reverted to previous stats',
                    )
                    embed.set_footer(
                        text=f'Reverted by {interaction.user.name}',
                        icon_url=interaction.user.display_avatar.url,
                    )

                    # Send reverted match log
                    if interaction.channel_id == config.TCGConfig.TCG_MATCH_REPORT_CHANNEL_ID:
                        match_log_channel = interaction.guild.get_channel(
                            config.TCGConfig.TCG_MATCH_LOG_CHANNEL_ID
                        )
                        await match_log_channel.send(embed=embed)

                    return await interaction.followup.send(embed=embed)

                else:
                    return await interaction.followup.send(
                        content=f'Match history for {member.name} is not found.'
                    )

    else:
        await send_missing_permission_error_embed(interaction)


async def set_member_stats(
    self,
    interaction: Interaction,
    member: Union[discord.Member, discord.User],
    win_count: Optional[app_commands.Range[int, 0]],
    loss_count: Optional[app_commands.Range[int, 0]],
    elo: Optional[app_commands.Range[float, 0]],
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;", member.id
            )
            if not res:
                await send_user_not_registered_error_embed(interaction, member.id)

            else:
                await conn.execute(
                    f"UPDATE tcg_leaderboard SET win_count={win_count if win_count else 'win_count'}, "
                    + f"loss_count={loss_count if loss_count else 'loss_count'}, "
                    + f"elo={elo if elo else 'elo'}  WHERE discord_id = {member.id};"
                )

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    description=f'{member.mention} stats has been set.',
                    timestamp=datetime.datetime.now(),
                )
                embed.set_footer(
                    text=f'Set by {interaction.user.name}',
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=embed)
    else:
        custom_description = (
            f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}>, <@&{config.ADMINISTRATOR_ROLE_ID['mod']}>, "
            + f"atau <@&{config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID}> yang bisa menggunakan command ini."
        )
        await send_missing_permission_error_embed(
            interaction, custom_description=custom_description
        )
