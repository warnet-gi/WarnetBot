import datetime
from venv import logger

import discord
from asyncpg import Pool
from discord import Interaction, app_commands

from bot import config
from bot.bot import WarnetBot
from bot.cogs.ext.tcg.utils import (
    calculate_elo,
    change_tcg_title_role,
    send_missing_permission_error_embed,
    send_user_is_not_in_guild_error_embed,
    send_user_not_registered_error_embed,
)
from bot.cogs.views.general import Confirm
from bot.helper import (
    no_channel_alert,
    no_guild_alert,
    no_permission_alert,
    value_is_none,
)


async def register_member(
    db_pool: Pool, interaction: Interaction, member: discord.Member | discord.User
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if (
        not interaction.user.guild_permissions.administrator
        and not interaction.user.get_role(config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID)
    ):
        await no_permission_alert(interaction=interaction)
        return

    member_id = member.id
    embed: discord.Embed
    async with db_pool.acquire() as conn:
        res = await conn.fetchval(
            "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
            member_id,
        )
        if not res:
            await conn.execute(
                "INSERT INTO tcg_leaderboard(discord_id) VALUES ($1);", member_id
            )
            embed = discord.Embed(
                color=discord.Colour.green(),
                title="✅ Registered successfully",
                description=f"{member.mention} sudah terdaftar di database TCG WARNET dan rating ELO miliknya sudah diatur menjadi 1500 by default.",
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )
        else:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title="❌ member is already registered",
                description=f"Akun {member.mention} sudah terdaftar. Tidak perlu didaftarkan lagi.",
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )

    await interaction.followup.send(embed=embed)


async def unregister_member(
    db_pool: Pool, interaction: Interaction, member: discord.Member | discord.User
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if not interaction.user.guild_permissions.administrator:
        await no_permission_alert(interaction=interaction)
        return

    member_id = member.id
    embed: discord.Embed
    async with db_pool.acquire() as conn:
        res = await conn.fetchval(
            "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
            member_id,
        )
        if not res:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title="❌ member is already not registered",
                description=f"Akun {member.mention} tidak terdaftar sejak awal.",
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )

            await interaction.followup.send(embed=embed)

        else:
            embed = discord.Embed(
                color=discord.Colour.yellow(),
                description=f"Yakin akan menghapus {member.mention} dari leaderboard?",
            )
            view = Confirm()
            msg = await interaction.followup.send(embed=embed, view=view, wait=True)
            await view.wait()

            if not view.value:
                await msg.edit(content="**Time Out**", embed=None, view=None)

            elif view.value:
                await conn.execute(
                    "DELETE FROM tcg_leaderboard WHERE discord_id = $1;", member_id
                )

                await msg.edit(
                    content=f"✅ **Sukses menghapus {member.mention} dari leaderboard**",
                    embed=None,
                    view=None,
                )

            else:
                await msg.delete()


async def reset_member_stats(
    db_pool: Pool, interaction: Interaction, member: discord.Member | discord.User
) -> None:
    await interaction.response.defer()

    if not interaction.guild:
        await no_guild_alert(interaction=interaction)
        return

    if not interaction.channel:
        await no_channel_alert(interaction=interaction)
        return

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    user_id = member.id
    if interaction.user.guild_permissions.administrator:
        await no_permission_alert(interaction=interaction)
        return

    async with db_pool.acquire() as conn:
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
            msg = await interaction.followup.send(
                embed=embed, view=view, ephemeral=True, wait=True
            )
            await view.wait()

            if not view.value:
                await msg.edit(content="**Time Out**", embed=None, view=None)

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
                tcg_title_role_list = [
                    interaction.guild.get_role(role_id)
                    for role_id in config.TCGConfig.TCG_TITLE_ROLE_ID
                ]
                await member.remove_roles(*tcg_title_role_list)  # type: ignore intended

                await msg.edit(
                    content=f"✅ **Sukses melakukan reset progress TCG kepada {member.mention}**",
                    embed=None,
                    view=None,
                )

                notify_embed = discord.Embed(
                    color=discord.Color.default(),
                    description=f"TCG stats milik {member.mention} telah direset",
                    timestamp=datetime.datetime.now(tz=datetime.UTC),
                )
                notify_embed.set_footer(
                    text=f"Reset by {interaction.user.name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.channel.send(embed=notify_embed, reference=msg)

            else:
                await msg.delete()


async def reset_all_member_stats(db_pool: Pool, interaction: Interaction) -> None:
    await interaction.response.defer()

    if not interaction.guild:
        await no_guild_alert(interaction=interaction)
        return

    if not interaction.user.guild_permissions.administrator:
        await no_permission_alert(interaction=interaction)
        return

    async with db_pool.acquire() as conn:
        embed = discord.Embed(
            color=discord.Colour.yellow(),
            description="Yakin akan mereset ulang semua progress user?",
        )
        view = Confirm()
        msg = await interaction.followup.send(
            embed=embed, view=view, ephemeral=True, wait=True
        )
        await view.wait()

        if not view.value:
            await msg.edit(content="**Time Out**", embed=None, view=None)

        elif view.value:
            await msg.edit(
                content="<a:loading:747680523459231834> **Resetting the TCG database...**",
                embed=None,
                view=None,
            )

            # Remove tcg title role after reset
            records = await conn.fetch("SELECT * FROM tcg_leaderboard;")
            member_target_list = [dict(row) for row in records]
            for member_data in member_target_list:
                member_id = member_data["discord_id"]
                if interaction.guild.get_member(member_id):
                    member = interaction.guild.get_member(member_id)
                    if member and member_data["title"]:
                        member_tcg_role = interaction.guild.get_role(
                            member_data["title"]
                        )
                        if not member_tcg_role:
                            logger.error(
                                "role not found",
                                extra={"role_id": member_data["title"]},
                            )
                        else:
                            await member.remove_roles(member_tcg_role)

            await conn.execute(
                "UPDATE tcg_leaderboard SET win_count=0, loss_count=0, elo=1500, title=NULL;"
            )

            notify_embed = discord.Embed(
                color=discord.Color.blurple(),
                title="✅ Sukses melakukan reset progress TCG kepada semua member",
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )
            notify_embed.set_footer(
                text=f"Reset by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await msg.edit(content=None, embed=notify_embed, view=None)

        else:
            await msg.delete()


async def set_match_result(  # noqa: C901, PLR0912, FIX002 #TODO: improve this
    db_pool: Pool,
    match_history: list,
    interaction: Interaction,
    winner: discord.Member | discord.User,
    loser: discord.Member | discord.User,
) -> None:
    await interaction.response.defer()

    if not interaction.guild:
        await no_guild_alert(interaction=interaction)
        return

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        async with db_pool.acquire() as conn:
            res1 = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
                winner.id,
            )
            res2 = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
                loser.id,
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
                await interaction.followup.send(
                    content="Winner and Loser must be different user!"
                )
            else:
                records = await conn.fetch(
                    "SELECT * FROM tcg_leaderboard WHERE discord_id = $1 OR discord_id = $2;",
                    winner.id,
                    loser.id,
                )
                if dict(records[0])["discord_id"] == winner.id:
                    winner_data = dict(records[0])
                    loser_data = dict(records[1])
                else:
                    winner_data = dict(records[1])
                    loser_data = dict(records[0])

                # save the current data to history list for /undo-match-result command
                match_history.append([winner_data, loser_data])

                elo_diff = calculate_elo(winner_data["elo"], loser_data["elo"])
                elo_after_win = winner_data["elo"] + elo_diff
                elo_after_loss = loser_data["elo"] - elo_diff

                embed = discord.Embed(
                    title="Match Result",
                    color=discord.Color.blurple(),
                    timestamp=datetime.datetime.now(tz=datetime.UTC),
                )
                embed.add_field(
                    name=f"{winner.name} VS {loser.name}",
                    value=f"🏆 {winner.name} ({elo_after_win:.1f}) (+{elo_diff})\n❌ {loser.name} ({elo_after_loss:.1f}) (-{elo_diff})",
                )
                embed.set_footer(
                    text=f"Score added by {interaction.user}",
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=embed)

                # Send match log for event
                if (
                    interaction.channel_id
                    == config.TCGConfig.TCG_MATCH_REPORT_CHANNEL_ID
                ):
                    match_log_channel = interaction.guild.get_channel(
                        config.TCGConfig.TCG_MATCH_LOG_CHANNEL_ID
                    )
                    if not match_log_channel:
                        await value_is_none(
                            value="match_log_channel", interaction=interaction
                        )
                    else:
                        await match_log_channel.send(embed=embed)

                winner_current_tcg_role = None
                loser_current_tcg_role = None
                if winner_data["title"]:
                    winner_current_tcg_role = winner.get_role(winner_data["title"])
                if loser_data["title"]:
                    loser_current_tcg_role = loser.get_role(loser_data["title"])

                new_tcg_role = await change_tcg_title_role(
                    interaction, winner, winner_current_tcg_role, elo_after_win
                )
                await conn.execute(
                    "UPDATE tcg_leaderboard SET win_count=win_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_win,
                    new_tcg_role.id if new_tcg_role else None,
                    winner_data["discord_id"],
                )

                new_tcg_role = await change_tcg_title_role(
                    interaction, loser, loser_current_tcg_role, elo_after_loss
                )
                await conn.execute(
                    "UPDATE tcg_leaderboard SET loss_count=loss_count+1, elo=$1, title=$2 WHERE discord_id = $3;",
                    elo_after_loss,
                    new_tcg_role.id if new_tcg_role else None,
                    loser_data["discord_id"],
                )

    else:
        custom_description = (
            f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}>, <@&{config.ADMINISTRATOR_ROLE_ID['mod']}>, "
            f"atau <@&{config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID}> yang bisa menggunakan command ini."
        )
        await send_missing_permission_error_embed(
            interaction, custom_description=custom_description
        )


async def undo_match_result(  # noqa: C901, PLR0912, FIX002 # TODO: improve this
    bot: WarnetBot,
    db_pool: Pool,
    match_history: list,
    interaction: Interaction,
    member: discord.Member | discord.User,
) -> None:
    await interaction.response.defer()

    if len(match_history) == 0:
        return await interaction.followup.send(
            content=f"Match history for {member.name} is not found."
        )

    if not interaction.guild:
        return await no_guild_alert(interaction=interaction)

    if (
        not interaction.user.guild_permissions.administrator
        and not interaction.user.get_role(config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID)
    ):
        return await no_permission_alert(interaction=interaction)

    if isinstance(member, discord.User):
        member = await bot.fetch_user(member.id)

    async with db_pool.acquire() as conn:
        res = await conn.fetchval(
            "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
            member.id,
        )
        if not res:
            await send_user_not_registered_error_embed(interaction, member.id)

        else:
            winner: discord.User | discord.Member | None = None
            loser: discord.User | discord.Member | None = None

            # Search member in match history
            idx = len(match_history) - 1
            found = False
            while idx >= 0 and not found:
                winner_data, loser_data = match_history[idx]
                if (
                    winner_data["discord_id"] != member.id
                    and loser_data["discord_id"] != member.id
                ):
                    idx -= 1

                else:
                    found = True

                    if winner_data["discord_id"] == member.id:
                        winner = member
                        loser = interaction.guild.get_member(loser_data["discord_id"])
                        if not loser:
                            await bot.fetch_user(loser_data["discord_id"])

                    elif loser_data["discord_id"] == member.id:
                        loser = member
                        winner = interaction.guild.get_member(winner_data["discord_id"])
                        if not winner:
                            await bot.fetch_user(winner_data["discord_id"])

                    await conn.execute(
                        "UPDATE tcg_leaderboard SET win_count=$1, loss_count=$2, elo=$3, title=$4 WHERE discord_id = $5;",
                        winner_data["win_count"],
                        winner_data["loss_count"],
                        winner_data["elo"],
                        winner_data["title"],
                        winner_data["discord_id"],
                    )
                    await conn.execute(
                        "UPDATE tcg_leaderboard SET win_count=$1, loss_count=$2, elo=$3, title=$4 WHERE discord_id = $5;",
                        loser_data["win_count"],
                        loser_data["loss_count"],
                        loser_data["elo"],
                        loser_data["title"],
                        loser_data["discord_id"],
                    )

                    match_history.pop(idx)

            if found and winner and loser:
                embed = discord.Embed(
                    title="Match Reverted",
                    color=discord.Color.yellow(),
                    timestamp=datetime.datetime.now(tz=datetime.UTC),
                )
                embed.add_field(
                    name=f"{winner.name} VS {loser.name}",
                    value="Match has been reverted to previous stats",
                )
                embed.set_footer(
                    text=f"Reverted by {interaction.user.name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                # Send reverted match log
                if (
                    interaction.channel_id
                    == config.TCGConfig.TCG_MATCH_REPORT_CHANNEL_ID
                ):
                    match_log_channel = interaction.guild.get_channel(
                        config.TCGConfig.TCG_MATCH_LOG_CHANNEL_ID
                    )
                    if not match_log_channel:
                        await value_is_none(
                            value="match_log_channel", interaction=interaction
                        )
                    else:
                        await match_log_channel.send(embed=embed)

                return await interaction.followup.send(embed=embed)

            return await interaction.followup.send(
                content=f"Match history for {member.name} is not found."
            )
    return None


async def set_member_stats(
    db_pool: Pool,
    interaction: Interaction,
    member: discord.Member | discord.User,
    win_count: app_commands.Range[int, 0] | None,
    loss_count: app_commands.Range[int, 0] | None,
    elo: app_commands.Range[float, 0] | None,
) -> None:
    await interaction.response.defer()

    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    if interaction.user.guild_permissions.administrator or interaction.user.get_role(
        config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID
    ):
        async with db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT discord_id FROM tcg_leaderboard WHERE discord_id = $1;",
                member.id,
            )
            if not res:
                await send_user_not_registered_error_embed(interaction, member.id)

            else:
                query = """
                    UPDATE tcg_leaderboard
                    SET win_count = COALESCE($1, win_count),
                        loss_count = COALESCE($2, loss_count),
                        elo = COALESCE($3, elo)
                    WHERE discord_id = $4;
                """
                await conn.execute(query, win_count, loss_count, elo, member.id)

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    description=f"{member.mention} stats has been set.",
                    timestamp=datetime.datetime.now(tz=datetime.UTC),
                )
                embed.set_footer(
                    text=f"Set by {interaction.user.name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=embed)
    else:
        custom_description = (
            f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}>, <@&{config.ADMINISTRATOR_ROLE_ID['mod']}>, "
            f"atau <@&{config.TCGConfig.TCG_EVENT_STAFF_ROLE_ID}> yang bisa menggunakan command ini."
        )
        await send_missing_permission_error_embed(
            interaction, custom_description=custom_description
        )
