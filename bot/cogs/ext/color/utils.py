from typing import Optional

import discord
from discord import Interaction, Role
from discord.ext import commands


async def check_role_by_name_or_number(
    self: commands.Cog,
    interaction: Interaction,
    name: Optional[str],
    number: Optional[int],
) -> Optional[Role]:
    if name and number:
        return await interaction.response.send_message(
            "❌ Please use just `name` or just `number`. Not both!", ephemeral=True
        )

    elif name or number:
        if name:
            role_target = discord.utils.find(lambda r: r.name == name, interaction.guild.roles)
        elif number:
            try:
                role_target_id = self.custom_role_data_list[number - 1]
                role_target = interaction.guild.get_role(role_target_id)
            except IndexError:
                role_target = None

        if not role_target:
            return await interaction.response.send_message(
                "❌ Failed to find the color!\nPlease use `/warnet-color list` to see all the available colors.",
                ephemeral=True,
            )

        return role_target

    else:
        return await interaction.response.send_message(
            "❌ Please supply a color `name` or a color `number`!", ephemeral=True
        )
