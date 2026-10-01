import discord
from discord import Interaction, ui
from discord.enums import ButtonStyle

from bot.helper import reject_non_author


class ConfirmView(ui.View):
    """Reusable accept/cancel confirmation for destructive commands.

    Usage:
    ```
        view = ConfirmView(interaction.user)
        msg = await interaction.followup.send(embed=prompt, view=view, wait=True)
        view.message = msg
        await view.wait()
        if view.confirmed:
            ...  # True = accepted; False = cancelled; None = timed out
    ```
    Only the invoking user can press the buttons; anyone else gets the
    standard ephemeral notice. Future callers needing a confirmation gate
    reuse this view instead of adding one-shot confirm flags.
    """

    def __init__(
        self,
        author: discord.Member,
        *,
        timeout: float | None = 60,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
    ) -> None:
        super().__init__(timeout=timeout)
        self.author = author
        self.confirmed: bool | None = None
        self.message: discord.Message | None = None
        self.confirm_button.label = confirm_label
        self.cancel_button.label = cancel_label

    async def interaction_check(self, interaction: Interaction) -> bool:
        return not await reject_non_author(interaction, self.author)

    @ui.button(label="Confirm", style=ButtonStyle.red)
    async def confirm_button(self, interaction: Interaction, button: ui.Button) -> None:
        self.confirmed = True
        await self._finish(interaction)

    @ui.button(label="Cancel", style=ButtonStyle.gray)
    async def cancel_button(self, interaction: Interaction, button: ui.Button) -> None:
        self.confirmed = False
        await self._finish(interaction)

    def _disable_all(self) -> None:
        # children are all Buttons; isinstance keeps pyright honest
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True

    async def _finish(self, interaction: Interaction) -> None:
        self._disable_all()
        # callback interaction edits; timeout path uses self.message
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self) -> None:
        self._disable_all()
        # message may be deleted or never attached; teardown must never raise
        if self.message is None:
            return
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
