import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands

from bot.bot import WarnetBot


class Admin(commands.Cog):
    
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @app_commands.command(description='Shows basic information about the bot')
    async def about(self, interaction) -> None:
        """Shows basic information about the bot."""

        owner_url = 'https://discord.com/users/278821688894947328'
        github_project = 'https://github.com/Iqrar99/OP-Warnet-Bot'
        saweria_url = 'https://saweria.co/warnetGI'

        embed = discord.Embed(color=0x4e24d6)
        embed.set_author(name='OP Warnet Bot', url=github_project)
        embed.set_thumbnail(url='https://cdn.discordapp.com/avatars/278821688894947328/f3503af0e79e1c737661147d391633c6.png')  ## placeholder
        embed.add_field(name='DEV:', value=f"[monarch99#1999]({owner_url})", inline=False)

        view = ui.View()
        view.add_item(ui.Button(label='GITHUB', url=github_project, row=0))
        view.add_item(ui.Button(label='SAWERIA', url=saweria_url, row=0))

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))