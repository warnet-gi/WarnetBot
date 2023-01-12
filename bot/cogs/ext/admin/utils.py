from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from typing import Optional
from asyncpg.connection import Connection
from zoneinfo import ZoneInfo

import discord
from discord import Interaction

from bot.config import config


WARNING_ICON_URL = 'https://cdn.discordapp.com/attachments/774322083319775262/1038314815929724989/unknown.png'


async def send_missing_permission_error_embed(interaction: Interaction, custom_description: str = None) -> None:
    description = f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini."
    if custom_description:
        description = custom_description

    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ You don't have permission",
        description=description,
        timestamp=datetime.now(),
    )

    await interaction.followup.send(embed=embed)


async def send_warn_message_to_member(
    interaction: Interaction,
    member: discord.Member,
    warn_level: int,
    reason: Optional[str],
    expiration_date: int  # POSIX time
) -> None:
    """DM member for the warning."""
    
    dm_channel: discord.DMChannel = member.create_dm()
    author = interaction.user

    warning_embed = discord.Embed(
        title="⚠️ You got a warning!",
        description="Admin/Mod telah memberikan peringatan kepadamu.",
        color=discord.Color.yellow(),
        timestamp=datetime.now(),
    )
    warning_embed.set_thumbnail(url=WARNING_ICON_URL)
    warning_embed.add_field(name='Warn Level', value=f'`{warn_level}`', inline=False)
    warning_embed.add_field(
        name='Reason',
        value=reason if reason is not None else '-',
        inline=False
    )
    warning_embed.add_field(
        name='Warning Expiration Time',
        value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
        inline=False
    )
    warning_embed.set_footer(
        text=f'Warned by {str(author)}',
        icon_url=author.display_avatar.url
    )

    await dm_channel.send(embed=warning_embed)


async def send_warn_log(
    interaction: Interaction,
    member: discord.Member,
    warn_level: int,
    reason: Optional[str],
    expiration_date: int  # POSIX time
) -> None:
    """Log every warning action."""

    author = interaction.user

    log_embed = discord.Embed(
        title='Member has been warned',
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )
    log_embed.set_thumbnail(url=member.display_avatar.url)
    log_embed.add_field(name='Warn Level', value=f'`{warn_level}`', inline=False)
    log_embed.add_field(
        name='Reason',
        value=reason if reason is not None else '-',
        inline=False
    )
    log_embed.add_field(
        name='Warning Expiration Time',
        value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
        inline=False
    )
    log_embed.set_footer(
        text=f'Warned by {str(author)}',
        icon_url=author.display_avatar.url
    )
    warn_log_channel = interaction.guild.get_channel(config.WarnConfig.WARN_LOG_CHANNEL_ID)
    await warn_log_channel.send(embed=log_embed)


# alur: simpan role member -> mute member (copot semua role dan tambahkan role mute) ->
# simpan data org yang kena mute di database -> kasih tahu kalau dia kena mute ->
# bikin job buat cek status mute dia setelah beberapa hari -> unmute
#
# edge case: member keluar server setelah kena mute sampai job pengecekan datang
# edge case: member keluar server setelah kena mute lalu kembali lagi sebelum job pengecekan datang
async def mute_member(
    scheduler: AsyncIOScheduler,
    interaction: Interaction,
    member: discord.Member,
    db_conn: Connection,
    days: Optional[int],
    reason: str
) -> None:
    muted_role = interaction.guild.get_role(config.WarnConfig.MUTED_ROLE_ID)
    booster_role = interaction.guild.get_role(config.BOOSTER_ROLE_ID)
    member_role_id_list = [role.id for role in member.roles]

    if member.get_role(config.BOOSTER_ROLE_ID):
        await member.edit(roles=[booster_role])
    else:
        await member.edit(roles=[])    
    await member.add_roles(muted_role)

    date_given = datetime.now(ZoneInfo('Asia/Jakarta'))
    date_expire = date_given + timedelta(days=days)
    await db_conn.execute(
        "INSERT INTO muted_members(discord_id, date_given, date_expire, reason, roles_store) VALUES ($1, $2, $3, $4, $5);",
        member.id,
        date_given,
        date_expire,
        reason,
        member_role_id_list
    )

    # TODO: DM member to inform they are being muted
    posix_date_expire = int(date_expire.timestamp())
    await send_mute_message_to_member(member, reason, posix_date_expire)

    # TODO: Add apscheduler to run job to unmute member 
    scheduler.add_job()


async def send_mute_message_to_member(
    member: discord.Member,
    reason: Optional[str],
    expiration_date: int  # POSIX time
) -> None:
    """DM member for the mute."""
    
    dm_channel: discord.DMChannel = member.create_dm()

    mute_embed = discord.Embed(
        title="⚠️ You have been muted!",
        description="Admin/Mod telah memberikan mute kepadamu.",
        color=discord.Color.orange(),
        timestamp=datetime.now(),
    )
    mute_embed.set_thumbnail(url=WARNING_ICON_URL)
    mute_embed.add_field(
        name='Reason',
        value=reason if reason is not None else '-',
        inline=False
    )
    mute_embed.add_field(
        name='Mute Expiration Time',
        value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
        inline=False
    )

    await dm_channel.send(embed=mute_embed)


async def check_warn_status(member: discord.member) -> None:
    pass