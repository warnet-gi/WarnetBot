from typing import Optional
from datetime import datetime, timedelta
import pytz
import time
import random
import io

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.bot import WarnetBot


class General(commands.Cog):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context) -> None:
        await ctx.send(f"🏓 **Pong!** Your ping is `{round(self.bot.latency * 1000)}` ms")

    @commands.hybrid_command(description='Shows basic information about the bot.')
    async def about(self, ctx: commands.Context) -> None:
        saweria_url = 'https://saweria.co/warnetGI'

        uptime = str(timedelta(seconds=int(round(time.time() - self.bot.start_time))))

        embed = discord.Embed(color=0x4E24D6)
        embed.set_author(
            name='Warnet Bot',
            icon_url='https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png',
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name='Developer', value=f"monarch99#1999", inline=False)
        embed.add_field(name='Contributor', value=f"Irvan#1845", inline=False)
        embed.add_field(name='Uptime', value=uptime, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label='Donate to WarnetGI Saweria', url=saweria_url, row=0))

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(description='Shows all commands that available to use.')
    async def help(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            color=ctx.author.color,
            title='📔 WarnetBot Wiki',
            description='WarnetBot Wiki merupakan dokumentasi command yang tersedia di bot. Kamu dapat mengakses dokumentasi bot ini melalui link di bawah.',
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name='👥 General Commands',
            value="[Link dokumentasi](https://github.com/Iqrar99/WarnetBot/wiki/Bot-Commands#-general-commands)",
            inline=False,
        )
        embed.add_field(
            name='🎲 TCG Commands',
            value="[Link dokumentasi](https://github.com/Iqrar99/WarnetBot/wiki/Bot-Commands#-tcg-commands)",
            inline=False,
        )
        embed.add_field(
            name='🧷 Sticky Command',
            value="[Link dokumentasi](https://github.com/Iqrar99/WarnetBot/wiki/Bot-Commands#-sticky-commands)",
            inline=False,
        )
        embed.add_field(
            name='✨ Khaenriah Command',
            value="[Link dokumentasi](https://github.com/Iqrar99/WarnetBot/wiki/Bot-Commands#-khaenriah-commands)",
            inline=False,
        )
        embed.add_field(
            name='👮 Admin Commands',
            value="[Link dokumentasi](https://github.com/Iqrar99/WarnetBot/wiki/Bot-Commands#-admin-commands)",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.hybrid_command(
        name='rolemembers',
        aliases=['rm'],
        description='Shows all members associated with a given role.',
    )
    @app_commands.describe(role='Guild role that you want to see the members associated in it.')
    async def role_members(self, ctx: commands.Context, role: discord.Role) -> None:
        await ctx.typing()
        content = f"Members with **{role.name}** role\n"
        content += "```arm\n"
        members_content = ''
        if role.members:
            for member in role.members:
                members_content += f"{str(member)} ({member.id})\n"
            content += members_content
        else:
            content += "No members associated with this role"
        content += "```"

        if len(content) > 2000:
            buffer = io.BytesIO(members_content.encode('utf-8'))
            await ctx.reply(
                content=f"Members with **{role.name}** role",
                file=discord.File(buffer, filename=f"{role.name}.txt"),
                mention_author=False,
            )
            buffer.close()

        else:
            await ctx.reply(content=content, mention_author=False)

    @app_commands.command(
        name='unix-timestamp',
        description='Get a UNIX timestamp to be used on discord timestamp format.',
    )
    @app_commands.describe(
        day='Set specific day. Default is today.',
        month='Set specific month. Default is current month.',
        year='Set specific year. Default is current year.',
        hour='Set specific hour. Default is current hour.',
        minute='Set specific minute. Default is current minute.',
        idn_timezone='Your Indonesia timezone',
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
        day: Optional[app_commands.Range[int, 1, 31]],
        month: Optional[app_commands.Range[int, 1, 12]],
        year: Optional[app_commands.Range[int, 1970]],
        hour: Optional[app_commands.Range[int, 0, 23]],
        minute: Optional[app_commands.Range[int, 0, 59]],
        idn_timezone: app_commands.Choice[int] = 7,
    ) -> None:
        idn_tz_code = {
            7: pytz.timezone('Asia/Jakarta'),
            8: pytz.timezone('Asia/Shanghai'),
            9: pytz.timezone('Asia/Jayapura'),
        }
        idn_tz = (
            idn_tz_code[idn_timezone]
            if not isinstance(idn_timezone, app_commands.Choice)
            else idn_tz_code[idn_timezone.value]
        )

        current_time = datetime.now(tz=pytz.utc).astimezone(idn_tz)
        day = current_time.day if day is None else day
        month = current_time.month if month is None else month
        year = current_time.year if year is None else year
        hour = current_time.hour if hour is None else hour
        minute = current_time.minute if minute is None else minute

        try:
            idn_dt = idn_tz.localize(datetime(year, month, day, hour=hour, minute=minute))
        except ValueError:
            return await interaction.response.send_message(
                content="Waktu dan tanggal yang dimasukkan ada yang salah. Silakan periksa kembali.",
                ephemeral=True,
            )

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

    @commands.command()
    async def nobar(self, ctx: commands.Context) -> None:
        NOBAR_CHANNEL_ID = 1092630886127783957
        OPEN_TICKET_CHANNEL_ID = 1066618888462278657
        nobar_role = ctx.guild.get_role(1093508844551942144)

        await ctx.channel.send(
            f"Tata cara menjadi **HOST NOBAR** di server {ctx.guild.name}:\n"
            f"1.  Silahkan ajukan tiket **Kontak Admin dan Mod** di <#{OPEN_TICKET_CHANNEL_ID}>.\n"
            f"2. Tentukan **Judul Film**, **Tanggal**, dan **Jam** nobar. Minimal __satu hari sebelum nobar__, agar dapat diumumkan kepada role **{nobar_role.name}** terlebih dahulu.\n"
            f"3. Pada saat waktu nobar, Admin/Mod akan memberikan kamu akses agar dapat stream pada channel <#{NOBAR_CHANNEL_ID}>."
        )

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._change_presence.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error) -> None:
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound,)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(content='**Role not found!**')

    @tasks.loop(minutes=2)
    async def _change_presence(self) -> None:
        humans = 0
        for g in self.bot.guilds:
            humans += sum(not m.bot for m in g.members)

        activity_status = [
            discord.Game(name='PC WARNET'),
            discord.Game(name='Genshin Impact'),
            discord.Game(name='Arknights'),
            discord.Game(name='Honkai: Star Rail'),
            discord.Activity(type=discord.ActivityType.listening, name=f'war! help'),
            discord.Activity(type=discord.ActivityType.watching, name=f'{humans} Pengguna WARNET'),
            discord.Activity(type=discord.ActivityType.competing, name='Spiral Abyss'),
        ]
        discord_status = [
            discord.Status.online,
            discord.Status.idle,
            discord.Status.do_not_disturb,
        ]

        await self.bot.change_presence(
            status=random.choice(discord_status), activity=random.choice(activity_status)
        )


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(General(bot))
