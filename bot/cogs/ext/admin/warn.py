from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Union

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.config import config
from bot.cogs.ext.admin.utils import (
    send_warn_message_to_member,
    send_warn_log,
    mute_member,
    decrease_warn_status
)
from bot.cogs.ext.tcg.utils import (
    send_user_is_not_in_guild_error_embed,
) 

# alur warn: cek apakah ni orang pernah di warn atau belum ->
    # Kalau belum: cek level warn -> kalau >1 maka mute dulu -> kasih role warn -> catat member yang kena warn di database
    # -> kirim pesan ke member kalau dia kena warn -> kirim log warn ke channel log -> bikin job buat cek status warn
    # -> turunkan level warn

    # kalau sudah pernah: cek level warn apakah lebih tinggi atau sama
        # Kalau lebih tinggi: kasih role warn lebih tinggi
        # Kalau sama atau lebih rendah: kasih pemberitahuann ke admod -> exit
    # -> update member yang kena warn di database -> kirim pesan ke member kalau dia kena warn
    # -> kirim log warn ke channel log -> bikin job buat cek status warn -> turunkan level warn
# TODO edge case: member keluar server setelah kena warn sampai job pengecekan datang
# TODO edge case: member keluar server setelah kena warn lalu kembali lagi sampai job pengecekan datang
async def admin_warn_give(
    self: commands.Cog,
    interaction: Interaction,
    member: Union[discord.Member, discord.User],
    warn_level: app_commands.Range[int, 1, 3],
    reason: Optional[str]
) -> None:
    interaction.response.defer()
    
    if isinstance(member, discord.User):
        await send_user_is_not_in_guild_error_embed(interaction, member)
        return

    scheduler: AsyncIOScheduler = self.scheduler

    async with self.db_pool.acquire() as conn:
        res = await conn.fetchval("SELECT * FROM warned_members WHERE discord_id = $1;", member.id)
        # First time warning for a member
        if res is None:
            if warn_level > 1:
                mute_days = [3, 7]
                await mute_member(scheduler, interaction, member, conn, days=mute_days[warn_level-2], reason=f'Warn {warn_level}')
                # TODO

            warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{warn_level}'])
            await member.add_roles(warn_role, reason)

            date_given = datetime.now(ZoneInfo('Asia/Jakarta'))
            date_expire = date_given + timedelta(days=30)
            await conn.execute(
                'INSERT INTO warned_members(discord_id, warn_level, date_given, date_expire) VALUES ($1, $2, $3, $4);',
                member.id,
                warn_level,
                date_given,
                date_expire,
            )

            posix_date_expire = int(date_expire.timestamp())
            await send_warn_message_to_member(interaction, member, warn_level, reason, posix_date_expire)
            await send_warn_log(interaction, member, warn_level, reason, posix_date_expire)

        # Member has been warned before
        else:
            member_status = dict(res)
            current_warn_level = member_status['warn_level']

            if warn_level <= current_warn_level:
                invalid_warn_notice_embed = discord.Embed(
                    title='⚠️ Warn level must be higher than the current one',
                    description=f'Tidak dapat memberikan **warn level {warn_level}** kepada user {str(member)} yang memiliki **warn level {current_warn_level}**.',
                    color=discord.Color.yellow()
                )
                return await interaction.followup.send(embed=invalid_warn_notice_embed)
            
            else:
                current_warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{current_warn_level}'])
                warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{warn_level}'])
                await member.remove_roles(current_warn_role)
                await member.add_roles(warn_role, reason)

                mute_days = [3, 7]
                await mute_member(scheduler, interaction, member, conn, days=mute_days[warn_level-2], reason=f'Warn {warn_level}')

                date_given = datetime.now(ZoneInfo('Asia/Jakarta'))
                date_expire = date_given + timedelta(days=30)
                await conn.execute(
                    "UPDATE warned_members SET warn_level=$1, date_given=$2, date_expire=$3, leave_server=0 WHERE discord_id = $4;",
                    warn_level,
                    date_given,
                    date_expire,
                    member.id
                )

                posix_date_expire = int(date_expire.timestamp())
                await send_warn_message_to_member(interaction, member, warn_level, reason, posix_date_expire)
                await send_warn_log(interaction, member, warn_level, reason, posix_date_expire)
    
    # TODO: Add scheduler to check the warn status
    scheduler.add_job(decrease_warn_status, trigger='date', args=[self, member], id=f'derease_warn-{str(member)}', replace_existing=True, run_date=date_expire)