from typing import Optional

import discord
from discord import Interaction, Role

from bot.cogs.color import Color


async def check_role_by_name_or_number(
    self: Color,
    interaction: Interaction,
    name: Optional[str],
    number: Optional[int],
) -> tuple[bool, Optional[Role]]:
    if name and number:
        await interaction.response.send_message(
            "❌ Please use just `name` or just `number`. Not both!", ephemeral=True
        )
        return False, None

    elif name or number:
        valid = False
        
        if name:
            role_target = discord.utils.find(lambda r: r.name == name, interaction.guild.roles)
            if role_target:
                if self.custom_role_data.get(role_target.id, None):
                    valid = True

        elif number:
            try:
                # color list index is not zero-based
                role_target_id = self.custom_role_data_list[number - 1]
                role_target = interaction.guild.get_role(role_target_id)
                valid = True

            except IndexError:
                valid = False

        if valid:
            return valid, role_target
        else:
            await interaction.response.send_message(
                "❌ Failed to find the color!\nPlease use `/warnet-color list` to see all the available colors.",
                ephemeral=True,
            )
            return False, None
        
    else:
        await interaction.response.send_message(
            "❌ Please supply a color `name` or a color `number`!", ephemeral=True
        )
        return False, None
