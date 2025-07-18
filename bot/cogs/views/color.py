from io import BytesIO

import discord
from discord import Interaction

from bot.cogs.ext.color.utils import no_permission_alert


class AcceptIconAttachment(discord.ui.View):
    def __init__(self, role, bytes):
        super().__init__(timeout=3600)
        self.role: discord.Role = role
        self.bytes: BytesIO = bytes

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def add_role_icon(
        self, interaction: Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_roles:
            return await no_permission_alert(interaction)

        try:
            edited_role = await self.role.edit(
                display_icon=self.bytes.getvalue(),
                reason=f"Approved by {interaction.user.name}",
            )
        except discord.HTTPException:
            return await interaction.followup.send(
                "Failed to update role icon. Please try again later. Make sure the bot has higher role than the role you want to edit.",
                ephemeral=True,
            )

        if edited_role:
            embed = discord.Embed(
                title="Role Icon Updated",
                description=f"Role {edited_role.mention} icon has been updated.",
                color=discord.Color.green(),
            )
            embed.set_footer(
                text=f"Accepted by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url,
            )

            button.label = "Accepted"
            button.disabled = True
            await interaction.message.edit(view=self)

            self.stop()
            await interaction.followup.send(embed=embed)
