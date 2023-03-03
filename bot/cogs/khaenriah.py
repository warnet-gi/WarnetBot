import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot


@commands.guild_only()
class Khaenriah(commands.Cog):
    BURONAN_ROLE_ID = 1022747195088318505

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.group(name='buronan', aliases=['buron'])
    async def buronan(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @buronan.command(name='warn')
    async def buronan_warn(self, ctx: commands.Context, member: discord.Member) -> None:
        pass

    @buronan.command(name='increase', aliases=['inc'])
    async def buronan_increase(self, ctx: commands.Context, member: discord.Member) -> None:
        pass

    @buronan.command(name='decrease', aliases=['dec'])
    async def buronan_decrease(self, ctx: commands.Context, member: discord.Member) -> None:
        pass

    @buronan.command(name='list')
    async def buronan_list(self, ctx: commands.Context) -> None:
        pass


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Khaenriah(bot))
