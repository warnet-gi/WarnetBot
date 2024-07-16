from io import BytesIO
from math import e
import discord
from discord import Interaction

from bot.cogs.ext.color.utils import no_permission_alert


class AcceptIconAttachment(discord.ui.View):
    def __init__(self, role, bytes):
        super().__init__(timeout=10800)
        self.role: discord.Role = role
        self.bytes: BytesIO = bytes

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def add_role_icon(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if (
            not interaction.user.premium_since
            and not interaction.user.guild_permissions.manage_roles
        ):
            return await no_permission_alert(interaction)

        edited_role = await self.role.edit(display_icon=self.bytes.getvalue())
        if edited_role:
            embed = discord.Embed(
                title="Role Icon Updated",
                description=f"Role {edited_role.mention} icon has been updated.",
                color=discord.Color.green(),
            )

            button.label = "Accepted"
            button.disabled = True
            await interaction.message.edit(view=self)

            self.stop()
            await interaction.followup.send(embed=embed)
