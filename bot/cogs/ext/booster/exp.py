import asyncio
import io
import logging
from datetime import date, datetime

import aiohttp
import discord

from bot.bot import TatsuApi, WarnetBot
from bot.config import (
    ADMIN_CHANNEL_ID,
    ANNOUNCEMENT_CHANNEL_ID,
    BOOSTER_MONTHLY_EXP,
    BOOSTER_ROLE_ID,
    GUILD_ID,
    TATSU_LOG_CHANNEL_ID,
)

logger = logging.getLogger(__name__)


async def give_monthly_booster_exp(bot: WarnetBot) -> None:
    logger.info(f'MONTHLY EXP BOOSTER IS TRIGGERED: {date.strftime("%B %Y")}')

    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    tatsu_log_channel = bot.get_channel(TATSU_LOG_CHANNEL_ID)
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(BOOSTER_ROLE_ID)
    month = date.strftime("%B")
    member_tags = member_ids = member_error = ''
    success_count = error_count = 0

    for member in role.members:
        try:
            result = await TatsuApi().add_score(member.id, BOOSTER_MONTHLY_EXP)
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error(f"API key is invalid or expired: {e}")
                await admin_channel.send(
                    f"403, apikey sudah kadaluwarsa atau tidak valid.\n {success_count} dari {role.members.count()} member berhasil:\n\n{member_tags}"
                )
                break
            else:
                logger.error(f"Failed to add score for {member.id}: {e}")
                continue

        if result:
            success_count += 1
            member_tags += f"{member.mention}, "
            member_ids += f"{member.id} "
        else:
            error_count += 1
            member_error += f"{member.mention}, "

        await asyncio.sleep(1.5)

    if member_ids:
        embed = discord.Embed(
            title="<a:checklist:1077585402422112297> Score updated!",
            description=f"Successfully awarded `{BOOSTER_MONTHLY_EXP}` score to {role.mention} ({success_count} members)\n\n{member_tags}",
            timestamp=datetime.now(),
            color=discord.Color.green(),
        )
        embed.set_footer(
            text=guild.name,
            icon_url="https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png",
        )
        await tatsu_log_channel.send(embed=embed)

        buffer = io.BytesIO(member_ids.encode('utf-8'))
        file = discord.File(buffer, filename=f"{month}_honorary.txt")
        await admin_channel.send(
            content=(
                f"Exp Honorary bulanan sudah dibagikan!\n- Jumlah member berhasil: `{success_count}`\n"
                f"- Jumlah member error: `{error_count}`\nLog Honorary bulan {month}"
            ),
            file=file,
        )

    if member_error:
        embed = discord.Embed(
            title="[Monthly Booster] Error handling user",
            description=f"({error_count} members)\n\n{member_error}",
            color=discord.Color.red(),
        )

        await tatsu_log_channel.send(embed=embed)

    if len(role.members) == success_count:
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        await channel.send(
            f"## Halo {role.mention}!\n\nKami ingin memberi tahu kalian bahwa exp bulan ini sudah dibagikan sebesar **{BOOSTER_MONTHLY_EXP}**.\n"
            f"Terima kasih atas boostnya. Sehat selalu dan sampai jumpa di bulan berikutnya! ❤️"
        )

    else:
        await admin_channel.send(
            "Terdapat error saat memberikan exp bulanan ke Honorary Knight.\n**Announcement gagal dibuat**"
        )
