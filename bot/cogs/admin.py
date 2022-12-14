import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands

from bot.bot import WarnetBot

import datetime, time
from typing import Optional, Literal

class Admin(commands.Cog):
    
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @app_commands.command(description='Shows basic information about the bot')
    async def about(self, interaction) -> None:
        """Shows basic information about the bot."""

        uptime = str(datetime.timedelta(seconds=int(round(time.time()-self.bot.start_time))))  

        saweria_url = 'https://saweria.co/warnetGI'

        embed = discord.Embed(color=0x4e24d6)
        embed.set_author(name='Warnet Bot', icon_url='https://cdn.discordapp.com/attachments/761684443915485184/1038313075260002365/warnet_logo_putih.png')
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name='Developer', value=f"monarch99#1999", inline=False)
        embed.add_field(name='Uptime', value=uptime, inline=False)

        view = ui.View()
        view.add_item(ui.Button(label='Donate to WarnetGI Saweria', url=saweria_url, row=0))

        await interaction.response.send_message(embed=embed, view=view)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} command(s) {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))