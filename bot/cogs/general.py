import datetime, time
import random

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.bot import WarnetBot

class General(commands.Cog):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @app_commands.command(description='Shows basic information about the bot.')
    async def about(self, interaction) -> None:
        await interaction.response.defer()

        uptime = str(datetime.timedelta(seconds=int(round(time.time()-self.bot.start_time))))  

        saweria_url = 'https://saweria.co/warnetGI'

        embed = discord.Embed(color=0x4e24d6)
        embed.set_author(name='Warnet Bot', icon_url='https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png')
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name='Developer', value=f"monarch99#1999", inline=False)
        embed.add_field(name='Uptime', value=uptime, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label='Donate to WarnetGI Saweria', url=saweria_url, row=0))

        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(description='Shows all commands that available to use.')
    async def help(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        embed = discord.Embed(
            color=interaction.user.color,
            title='📔 Commands yang tersedia di WarnetBot',
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name='👥 General Commands',
            value="""
            `/help` - Shows all commands that available to use.
            `/about` - Shows basic information about the bot.
            """,
            inline=False
        )
        embed.add_field(
            name='👮 Admin Commands',
            value="""
            `/admin give-role-on-vc` - Give a role to all members in a voice channel.
            `war! ct` - Return channel topic where this command is executed.
            """,
            inline=False
        )
        embed.add_field(
            name='<:ImmortalDuelist:1052440404135518228> TCG Commands',
            value="""
            `/warnet-tcg register` - Member need to register before using other tcg commands.
            `/warnet-tcg member-stats` - Member can check their or someone else's TCG stats.
            `/warnet-tcg leaderboard` - ELO leaderboard for WARNET TCG.
            `/warnet-tcg register-member` - __**(ADMIN)**__ register a member manually if they haven't registered on TCG leaderboard yet.
            `/warnet-tcg unregister-member` - __**(ADMIN)**__ Unregister a member from TCG leaderboard.
            `/warnet-tcg reset-stats` - __**(ADMIN)**__ Reset a member TCG stats.
            `/warnet-tcg reset-all-stats` - __**(ADMIN)**__ Reset all member TCG stats.
            `/warnet-tcg set-match-result` - __**(ADMIN)**__ Set the TCG match result between players.
            `/warnet-tcg set-member-stats` - __**(ADMIN)**__ Set tcg stats for a member manually.
            """,
            inline=False
        )
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._change_presence.start()

    @tasks.loop(minutes=1)
    async def _change_presence(self) -> None:
        humans = 0
        for g in self.bot.guilds:
            humans += sum(not m.bot for m in g.members)

        activity_status = [
            discord.Game(name='PC WARNET'),
            discord.Activity(type=discord.ActivityType.watching, name=f'{humans} Pengguna WARNET'),
            discord.Activity(type=discord.ActivityType.competing, name='TCG WARNET OPEN'),
        ]
        discord_status = [
            discord.Status.online,
            discord.Status.idle,
            discord.Status.do_not_disturb,
        ]
        
        await self.bot.change_presence(
            status=random.choice(discord_status),
            activity=random.choice(activity_status)
        )


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(General(bot))