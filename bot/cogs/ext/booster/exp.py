import asyncio
import http
import io
import logging
from datetime import UTC, datetime

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


async def give_monthly_booster_exp(bot: WarnetBot) -> None:  # noqa: C901, PLR0912, PLR0915, FIX002 # TODO: improve this
    today = datetime.now(tz=datetime.UTC).date()
    logger.info(
        "MONTHLY EXP BOOSTER IS TRIGGERED", extra={"date": today.strftime("%B %Y")}
    )

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        logger.error("guild not found", extra={"id": GUILD_ID})
        return

    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    tatsu_log_channel = bot.get_channel(TATSU_LOG_CHANNEL_ID)
    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    role = guild.get_role(BOOSTER_ROLE_ID)
    month = today.strftime("%B")
    member_tags = member_ids = member_error = ""
    success_count = error_count = 0

    if not role:
        logger.error("role not found", extra={"id": BOOSTER_ROLE_ID})
        return

    if not admin_channel or not tatsu_log_channel or not announcement_channel:
        missing_channels = []
        if not admin_channel:
            missing_channels.append("admin_channel")
        if not tatsu_log_channel:
            missing_channels.append("tatsu_log_channel")
        if not announcement_channel:
            missing_channels.append("announcement_channel")

        logger.error(
            "Missing required channel(s): %s",
            ", ".join(missing_channels),
            extra={
                "admin_channel_id": ADMIN_CHANNEL_ID,
                "tatsu_log_channel_id": TATSU_LOG_CHANNEL_ID,
                "announcement_channel_id": ANNOUNCEMENT_CHANNEL_ID,
            },
        )
        return

    for member in role.members:
        try:
            await TatsuApi().add_score(member.id, BOOSTER_MONTHLY_EXP)

            success_count += 1
            member_tags += f"{member.mention}, "
            member_ids += f"{member.id} "

        except aiohttp.ClientResponseError as e:
            if e.status == http.HTTPStatus.UNAUTHORIZED:
                logger.exception("API key is invalid or expired")
                await admin_channel.send(
                    f"403, apikey sudah kadaluwarsa atau tidak valid.\n {success_count} dari {len(role.members)} member berhasil:\n\n{member_tags}"
                )
                break
            logger.exception("Failed to add score for", extra={"member_id": member.id})
            error_count += 1
            member_error += f"{member.mention}, "
            continue
        except Exception:
            logger.exception("Failed to add score for", extra={"member_id": member.id})
            error_count += 1
            member_error += f"{member.mention}, "
            continue

        await asyncio.sleep(1.5)

    if member_ids:
        embed = discord.Embed(
            title="<a:checklist:1077585402422112297> Score updated!",
            description=f"Successfully awarded `{BOOSTER_MONTHLY_EXP}` score to {role.mention} ({success_count} members)\n\n{member_tags}",
            timestamp=datetime.now(tz=UTC),
            color=discord.Color.green(),
        )
        embed.set_footer(
            text=guild.name,
            icon_url="https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png",
        )
        await tatsu_log_channel.send(embed=embed)

        buffer = io.BytesIO(member_ids.encode("utf-8"))
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
        await announcement_channel.send(
            f"## Halo {role.mention}!\n\nKami ingin memberi tahu kalian bahwa exp bulan ini sudah dibagikan sebesar **{BOOSTER_MONTHLY_EXP}**.\n"
            f"Terima kasih atas boostnya. Sehat selalu dan sampai jumpa di bulan berikutnya! ❤️"
        )

    else:
        await admin_channel.send(
            "Terdapat error saat memberikan exp bulanan ke Honorary Knight.\n**Announcement gagal dibuat**"
        )
