import datetime

import discord
from discord import Interaction
from discord.ext import commands

from bot.cogs.ext.admin.utils import send_missing_permission_error_embed


async def admin_give_role_on_vc(self: commands.Cog, interaction: Interaction, vc: discord.VoiceChannel, role: discord.Role) -> None:
    await interaction.response.defer()

    if interaction.user.guild_permissions.administrator:
        cnt = 0
        for member in vc.members:
            if member.get_role(role.id) is None:
                await member.add_roles(role)
                cnt += 1

        embed = discord.Embed(
            color=discord.Color.green(),
            title='✅ Role successfully given',
            description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di voice channel {vc.mention}.",
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(
            text=f'Given by {str(interaction.user)}',
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.followup.send(embed=embed)

    else:
        await send_missing_permission_error_embed(interaction)
