import logging

import discord
from discord import ui

logger = logging.getLogger(__name__)


class Feedback(discord.ui.Modal, title="Feedback"):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="Your name here...",
    )

    feedback = discord.ui.TextInput(
        label="What do you think of this new feature?",
        style=discord.TextStyle.long,
        placeholder="Type your feedback here...",
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"Thanks for your feedback, {self.name.value}!", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            "Oops! Something went wrong.", ephemeral=True
        )
        logger.error("Error in Feedback Modal", exc_info=error)


class TestButton(ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(Feedback())


class Components(discord.ui.LayoutView):
    container1 = discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(content="Show details of your current custom role"),
            accessory=discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Current Color",
                custom_id="current_color_button_color_v2",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.Section(
            discord.ui.TextDisplay(content="Show all roles created by you"),
            accessory=discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="My Colors",
                custom_id="my_color_button_color_v2",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.Section(
            discord.ui.TextDisplay(content="Change your color icon"),
            accessory=discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Change Icon",
                custom_id="change_icon_button_color_v2",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.Section(
            discord.ui.TextDisplay(content="Show all available custom roles"),
            accessory=discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="List All Colors",
                custom_id="list_all_color_button_color_v2",
            ),
        ),
    )
