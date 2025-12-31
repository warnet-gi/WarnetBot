import io
import logging
import random
import time
from datetime import UTC, datetime, timedelta

import discord
import pytz
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.helper import value_is_none

logger = logging.getLogger(__name__)


class General(commands.Cog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        logger.exception("An unexpected error occurred in Admin cog", exc_info=error)
        await ctx.reply(
            "An unexpected error occurred. Please try again later.",
            delete_after=5,
            ephemeral=True,
        )

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        await ctx.send(
            f"🏓 **Pong!** Your ping is `{round(self.bot.latency * 1000)}` ms"
        )

    @commands.hybrid_command(description="Shows basic information about the bot.")
    async def about(self, ctx: commands.Context) -> None:
        if self.bot.user is None:
            await value_is_none(value="self.bot.user", ctx=ctx)
            return

        saweria_url = "https://saweria.co/warnetGI"

        uptime = str(timedelta(seconds=round(time.time() - self.bot.start_time)))

        embed = discord.Embed(color=0x4E24D6)
        embed.set_author(
            name="Warnet Bot",
            icon_url="https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png",
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Developer", value="momonnie", inline=False)
        embed.add_field(
            name="Contributors",
            value=(
                "- [hilmoo](https://github.com/hilmoo)\n"
                "- [Irvan789](https://github.com/Irvan789)\n"
                "- [rafiramadhana](https://github.com/rafiramadhana)\n"
                "- [syhrimr](https://github.com/syhrimr)\n"
                "- [The5cheduler](https://github.com/The5cheduler)"
            ),
            inline=False,
        )
        embed.add_field(name="Uptime", value=uptime, inline=False)
        embed.add_field(name="Bot Version", value=self.bot.version, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Donate to WarnetGI Saweria", url=saweria_url, row=0
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(description="Shows all commands that available to use.")
    async def help(self, ctx: commands.Context) -> None:
        if self.bot.user is None:
            await value_is_none(value="self.bot.user", ctx=ctx)
            return

        embed = discord.Embed(
            color=ctx.author.color,
            title="📔 WarnetBot Wiki",
            description="WarnetBot Wiki merupakan dokumentasi command yang tersedia di bot. Kamu dapat mengakses dokumentasi bot ini melalui link di bawah.",
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="👮 Admin Commands",
            value="[Link dokumentasi](https://github.com/warnet-gi/WarnetBot/wiki/Bot-Commands#-admin-commands)",
            inline=False,
        )
        embed.add_field(
            name="👥 General Commands",
            value="[Link dokumentasi](https://github.com/warnet-gi/WarnetBot/wiki/Bot-Commands#-general-commands)",
            inline=False,
        )
        embed.add_field(
            name="🧷 Sticky Command",
            value="[Link dokumentasi](https://github.com/warnet-gi/WarnetBot/wiki/Bot-Commands#-sticky-commands)",
            inline=False,
        )
        embed.add_field(
            name="✨ Khaenriah Command",
            value="[Link dokumentasi](https://github.com/warnet-gi/WarnetBot/wiki/Bot-Commands#-khaenriah-commands)",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.hybrid_command(
        name="rolemembers",
        aliases=["rm"],
        description="Shows all members associated with a given role.",
    )
    @app_commands.describe(
        role="Guild role that you want to see the members associated in it.",
        id_only="Only return the discord ID without newline.",
    )
    async def role_members(
        self,
        ctx: commands.Context,
        role: discord.Role,
        id_only: bool | None,
    ) -> None:
        await ctx.typing()
        content = f"**{len(role.members)}** member(s) with **{role.name}** role\n"
        content += "```json\n"
        members_content = ""
        if role.members:
            for member in role.members:
                if not id_only:
                    members_content += f"{member.name} - {member.id}\n"
                else:
                    members_content += f"{member.id} "
            content += members_content
        else:
            content += "No member associated with this role"
        content += "```"

        max_size_file = 2000
        if len(content) > max_size_file:
            buffer = io.BytesIO(members_content.encode("utf-8"))
            await ctx.reply(
                content=f"**{len(role.members)}** member(s) with **{role.name}** role",
                file=discord.File(buffer, filename=f"{role.name}.txt"),
                mention_author=False,
            )
            buffer.close()

        else:
            await ctx.reply(content=content, mention_author=False)

    @app_commands.command(
        name="unix-timestamp",
        description="Get a UNIX timestamp to be used on discord timestamp format.",
    )
    @app_commands.describe(
        day="Set specific day. Default is today.",
        month="Set specific month. Default is current month.",
        year="Set specific year. Default is current year.",
        hour="Set specific hour. Default is current hour.",
        minute="Set specific minute. Default is current minute.",
        idn_timezone="Your Indonesia timezone",
    )
    @app_commands.choices(
        idn_timezone=[
            app_commands.Choice(name="WIB (GMT+7)", value=7),
            app_commands.Choice(name="WITA (GMT+8)", value=8),
            app_commands.Choice(name="WIT (GMT+9)", value=9),
        ]
    )
    async def unix_timestamp(
        self,
        interaction: Interaction,
        day: app_commands.Range[int, 1, 31] | None,
        month: app_commands.Range[int, 1, 12] | None,
        year: app_commands.Range[int, 1970] | None,
        hour: app_commands.Range[int, 0, 23] | None,
        minute: app_commands.Range[int, 0, 59] | None,
        idn_timezone: app_commands.Choice[int] | None,
    ) -> None:
        if idn_timezone is None:
            idn_timezone = app_commands.Choice(name="WIB (GMT+7)", value=7)

        idn_tz_code = {
            7: pytz.timezone("Asia/Jakarta"),
            8: pytz.timezone("Asia/Shanghai"),
            9: pytz.timezone("Asia/Jayapura"),
        }
        idn_tz = (
            idn_tz_code[idn_timezone]
            if not isinstance(idn_timezone, app_commands.Choice)
            else idn_tz_code[idn_timezone.value]
        )

        current_time = datetime.now(tz=pytz.utc).astimezone(idn_tz)
        day = day if day else current_time.day
        month = month if month else current_time.month
        year = year if year else current_time.year
        hour = current_time.hour if hour is None else hour
        minute = current_time.minute if minute is None else minute

        try:
            idn_dt = idn_tz.localize(
                datetime(year, month, day, hour=hour, minute=minute, tzinfo=UTC)
            )
        except ValueError:
            await interaction.response.send_message(
                content="Waktu dan tanggal yang dimasukkan ada yang salah. Silakan periksa kembali.",
                ephemeral=True,
            )
            return

        unix = int(idn_dt.timestamp())
        content = (
            f"`<t:{unix}>` = <t:{unix}>\n"
            f"`<t:{unix}:t>` = <t:{unix}:t>\n"
            f"`<t:{unix}:T>` = <t:{unix}:T>\n"
            f"`<t:{unix}:d>` = <t:{unix}:d>\n"
            f"`<t:{unix}:D>` = <t:{unix}:D>\n"
            f"`<t:{unix}:f>` = <t:{unix}:f>\n"
            f"`<t:{unix}:F>` = <t:{unix}:F>\n"
            f"`<t:{unix}:R>` = <t:{unix}:R>\n"
        )

        await interaction.response.send_message(content=content)
        return

    @commands.command()
    @commands.guild_only()
    async def nobar(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return

        nobar_channel_id = 1092630886127783957
        open_ticket_channel_id = 1066618888462278657
        nobar_role = ctx.guild.get_role(1093508844551942144)
        if nobar_role is None:
            logger.error(
                "Role not found",
                extra={"role_id": 1093508844551942144},
            )
            return

        await ctx.channel.send(
            f"Tata cara menjadi **HOST NOBAR** di server {ctx.guild.name}:\n"
            f"1. Silahkan ajukan tiket **Kontak Admin dan Mod** di <#{open_ticket_channel_id}>.\n"
            f"2. Tentukan **Judul Film**, **Tanggal**, dan **Jam** nobar. Minimal __satu hari sebelum nobar__, agar dapat diumumkan kepada role **{nobar_role.name}** terlebih dahulu.\n"
            f"3. Pada saat waktu nobar, Admin/Mod akan memberikan kamu akses agar dapat stream pada channel <#{nobar_channel_id}>."
        )
        return

    @commands.hybrid_command(
        name="calendar",
        aliases=["cal"],
        description="Shows HoYoverse calendar for Genshin, HSR, and ZZZ.",
    )
    async def calendar(self, ctx: commands.Context) -> None:
        await ctx.typing()
        embed = discord.Embed(
            title="HoYoverse 2026 Patch Calendar",
            color=ctx.author.color,
            description=(
                "For Genshin Impact, Honkai: Star Rail, and Zenless Zone Zero\n\n"
                "Dates are estimation based on previous versions' pattern, it may or may not change,\n\n"
                "if there are any changes in the future, this calendar will (eventually) be updated.\n\n"
                "Rev: 30/12/2025."
            ),
        )
        embed.set_image(
            url="https://raw.githubusercontent.com/warnet-gi/WarnetBot/main/bot/assets/img/calendar.png?hello"
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not self._change_presence.is_running():
            self._change_presence.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error) -> None:  # noqa: ANN001 'error' does not have a type annotation
        if hasattr(ctx.command, "on_error"):
            return

        ignored = (commands.CommandNotFound,)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(content="**Role not found!**")

    @tasks.loop(minutes=2)
    async def _change_presence(self) -> None:
        activity_status = [
            discord.Game(name="PC Warnet"),
            discord.Game(name="Genshin Impact"),
            discord.Game(name="Arknights"),
            discord.Game(name="Honkai: Star Rail"),
            discord.Game(name="Wuthering Waves"),
            discord.Activity(type=discord.ActivityType.listening, name="war! help"),
            discord.Activity(type=discord.ActivityType.competing, name="Spiral Abyss"),
            discord.Activity(
                type=discord.ActivityType.competing, name="Imaginarium Theater"
            ),
        ]
        discord_status = [
            discord.Status.online,
            discord.Status.idle,
            discord.Status.do_not_disturb,
        ]

        await self.bot.change_presence(
            status=random.choice(discord_status),  # noqa: S311
            activity=random.choice(activity_status),  # noqa: S311
        )


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(General(bot))
