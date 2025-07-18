import discord
from discord import Interaction


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Ya", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()

    @discord.ui.button(label="Tidak", style=discord.ButtonStyle.primary)
    async def cancel(self, interaction: Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
