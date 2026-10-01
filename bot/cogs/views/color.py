# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalOperand=false, reportArgumentType=false, reportCallIssue=false
import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import Interaction

from bot.config import CustomRoleConfig
from bot.helper import reject_non_author

logger = logging.getLogger(__name__)

HEX_COLOR_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")

# In-memory open icon requests: staff-ping message id -> role id.
# No DB persistence: entries die with the process (accepted scope limit). Expiry is the view's own timeout.
_PENDING: dict[int, int] = {}


def parse_hex_color(value: str) -> discord.Colour | None:
    """Strict 6-digit hex (# optional); None for anything else."""
    text = value.strip()
    if not HEX_COLOR_RE.match(text):
        return None
    return discord.Colour(int(text.lstrip("#"), 16))


class CustomRoleFormView(discord.ui.LayoutView):
    """Style picker + detail modal; the result dict feeds create/edit."""

    def __init__(
        self,
        author: discord.Member,
        *,
        mode: str,
        timeout: float | None = 300,
        current: dict | None = None,
    ) -> None:
        """Build the step flow: create picks style then details; edit picks scope first."""
        super().__init__(timeout=timeout)
        self.author = author
        self.mode = mode  # "create" or "edit"
        self.style: str | None = None
        self.scope: str | None = None  # edit mode only: "name" | "colors" | "both"
        self.current = current or {}
        self.result: dict[str, Any] | None = None
        self.message: discord.Message | None = None
        self.container = discord.ui.Container()
        if mode == "create":
            self.container.add_item(
                discord.ui.TextDisplay(
                    f"### Custom role {mode}\nPick a color style, then fill the form."
                ),
            )
            self.style_select = discord.ui.Select(
                placeholder="Color style",
                options=[
                    discord.SelectOption(label="Single color", value="single"),
                    discord.SelectOption(label="Gradient color", value="gradient"),
                ],
            )
            self.style_select.callback = self._style_callback
            self.open_button = discord.ui.Button(
                label="Fill role details",
                style=discord.ButtonStyle.blurple,
                disabled=True,
            )
            self.open_button.callback = self._open_callback
            self.container.add_item(discord.ui.ActionRow(self.style_select))
            self.container.add_item(discord.ui.ActionRow(self.open_button))
        else:
            self._intro_text = discord.ui.TextDisplay(
                f"### Custom role {mode}\nWhat do you want to edit?"
            )
            self.container.add_item(self._intro_text)
            scope_buttons = []
            for label, scope in (
                ("Name", "name"),
                ("Color", "colors"),
                ("Name and Color", "both"),
            ):
                button = discord.ui.Button(
                    label=label, style=discord.ButtonStyle.secondary
                )
                button.callback = self._make_scope_callback(scope)
                scope_buttons.append(button)
            self._scope_row = discord.ui.ActionRow(*scope_buttons)
            self.container.add_item(self._scope_row)
        self.add_item(self.container)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Only the invoking booster may touch the form."""
        return not await reject_non_author(interaction, self.author)

    def _make_scope_callback(
        self, scope: str
    ) -> Callable[[Interaction], Coroutine[Any, Any, None]]:
        """Bind one scope button to its modal flow."""

        async def _callback(interaction: Interaction) -> None:
            await self._scope_chosen(interaction, scope)

        return _callback

    async def _scope_chosen(self, interaction: Interaction, scope: str) -> None:
        """Name opens the modal at once; colors first swap in the style step."""
        self.scope = scope
        if scope == "name":
            await self._open_modal(
                interaction, scope, str(self.current.get("style") or "single")
            )
            return
        self.container.remove_item(self._intro_text)
        self.container.remove_item(self._scope_row)
        self.container.add_item(
            discord.ui.TextDisplay(f"### Custom role {self.mode}\nPick a color style.")
        )
        style_buttons = []
        for label, style in (
            ("Single color", "single"),
            ("Gradient color", "gradient"),
        ):
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)
            button.callback = self._make_style_callback(style)
            style_buttons.append(button)
        self.container.add_item(discord.ui.ActionRow(*style_buttons))
        await interaction.response.edit_message(view=self)

    def _make_style_callback(
        self, style: str
    ) -> Callable[[Interaction], Coroutine[Any, Any, None]]:
        """Bind one style button to its modal flow."""

        async def _callback(interaction: Interaction) -> None:
            self.style = style
            await self._open_modal(interaction, self.scope or "both", style)

        return _callback

    async def _open_modal(
        self, interaction: Interaction, scope: str, style: str
    ) -> None:
        """Open the detail modal for the resolved scope and style."""
        await interaction.response.send_modal(
            RoleFormModal(
                self,
                title=f"Custom role {self.mode}",
                style=style,
                scope=scope,
                current=self.current,
            ),
        )

    async def _style_callback(self, interaction: Interaction) -> None:
        """Create mode: remember the style and unlock the details button."""
        values = self.style_select.values
        self.style = values[0] if values else None
        labels = {"single": "Single color", "gradient": "Gradient color"}
        self.style_select.placeholder = labels.get(self.style, "Color style")
        for option in self.style_select.options:
            option.default = option.value == self.style
        self.open_button.disabled = self.style is None
        await interaction.response.edit_message(view=self)

    async def _open_callback(self, interaction: Interaction) -> None:
        """Create mode: open the full detail modal for the picked style."""
        await self._open_modal(interaction, "both", self.style or "single")

    async def on_timeout(self) -> None:
        """Freeze the form so a stale view can't submit."""
        for row in self.container.children:
            if isinstance(row, discord.ui.ActionRow):
                for item in row.children:
                    item.disabled = True
        # message may be deleted or never attached; teardown must never raise
        if self.message is None:
            self.stop()
            return
        try:
            await self.message.edit(view=self)
        except (discord.NotFound, discord.Forbidden):
            pass
        self.stop()


class RoleFormModal(discord.ui.Modal):
    """Name + hex inputs for one style; gradient adds the second hex field."""

    def __init__(
        self,
        form_view: "CustomRoleFormView",
        *,
        title: str,
        style: str,
        scope: str = "both",
        current: dict | None = None,
    ) -> None:
        super().__init__(title=title, timeout=300)
        self.form_view = form_view
        self.style = style  # snapshot at open; the select may move afterwards
        self.scope = scope
        self.current = current or {}
        want_name = scope in ("name", "both")
        want_colors = scope in ("colors", "both")
        self.name_input: discord.ui.TextInput | None = None
        self.primary_input: discord.ui.TextInput | None = None
        self.secondary_input: discord.ui.TextInput | None = None
        if want_name:
            self.name_input = discord.ui.TextInput(
                label="Role name",
                max_length=100,
                default=str(self.current.get("name") or ""),
            )
            self.add_item(self.name_input)
        if want_colors:
            self.primary_input = discord.ui.TextInput(
                label="Primary color hex",
                placeholder="#FF0000",
                max_length=7,
                default=str(self.current.get("primary") or ""),
            )
            self.add_item(self.primary_input)
        if want_colors and style == "gradient":
            self.secondary_input = discord.ui.TextInput(
                label="Secondary color hex",
                placeholder="#00FF00",
                max_length=7,
                default=str(self.current.get("secondary") or ""),
            )
            self.add_item(self.secondary_input)

    async def on_submit(self, interaction: Interaction) -> None:
        """Validate shown fields, inherit the rest, store the result, stop waiting."""
        if self.primary_input is None and self.secondary_input is None:
            style = str(self.current.get("style") or "single")
        else:
            style = self.style
        if self.name_input is not None:
            name = (self.name_input.value or "").strip()
            if not name:
                await interaction.response.send_message(
                    "Role name cannot be empty.",
                    ephemeral=True,
                )
                return
        else:
            name = str(self.current.get("name") or "")
        if self.primary_input is not None:
            primary = parse_hex_color(self.primary_input.value or "")
            if primary is None:
                await interaction.response.send_message(
                    "Primary color must be a hex like #FF0000.",
                    ephemeral=True,
                )
                return
        else:
            primary = parse_hex_color(str(self.current.get("primary") or ""))
            if primary is None:
                await interaction.response.send_message(
                    "Stored primary color is unreadable; edit colors instead.",
                    ephemeral=True,
                )
                return
        secondary: discord.Colour | None = None
        if style == "gradient":
            if self.secondary_input is not None:
                secondary = parse_hex_color(self.secondary_input.value or "")
                if secondary is None:
                    await interaction.response.send_message(
                        "Gradient needs a secondary hex like #00FF00.",
                        ephemeral=True,
                    )
                    return
            else:
                secondary = parse_hex_color(str(self.current.get("secondary") or ""))
        self.form_view.result = {
            "name": name,
            "style": style,
            "primary": primary,
            "secondary": secondary,
            "scope": self.scope,
        }
        await interaction.response.defer(ephemeral=True)
        self.form_view.stop()


class IconApprovalView(discord.ui.View):
    """Staff decision gate: any approver role or manage_roles; 15m auto-reject."""

    def __init__(
        self,
        *,
        role_id: int,
        owner_id: int,
        staff_role_ids: list[int],
        timeout: float | None = None,
    ) -> None:
        """Timeout defaults to the icon-expiry setting; decision starts undecided."""
        super().__init__(
            timeout=timeout
            if timeout is not None
            else float(CustomRoleConfig.ICON_EXPIRY_SECONDS),
        )
        self.role_id = role_id
        self.owner_id = owner_id
        self.staff_role_ids = staff_role_ids
        self.decision: str | None = None  # "approved" | "denied" | "expired"
        self.approver: discord.Member | None = None
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Any approver role or manage_roles passes; others get an ephemeral refuse."""
        member = interaction.user
        if isinstance(member, discord.Member):
            if any(role.id in self.staff_role_ids for role in member.roles):
                return True
            if member.guild_permissions.manage_roles:
                return True
        embed = discord.Embed(
            description="Only staff can review icon requests.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    def _disable_all(self) -> None:
        """Freeze every button after a decision or timeout."""
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def _claim(self, interaction: Interaction, decision: str) -> bool:
        """Take the one decision slot; refuses expired, superseded, or already-decided requests."""
        if (
            self.decision is not None
            or self.message is None
            or self.message.id not in _PENDING
        ):
            await interaction.response.send_message(
                "This request is no longer open.", ephemeral=True
            )
            return False
        self.decision = decision
        self.approver = (
            interaction.user if isinstance(interaction.user, discord.Member) else None
        )
        return True

    def _stamp_footer(
        self, interaction: Interaction, verb: str
    ) -> discord.Embed | None:
        """Mark who decided directly on the original request embed's footer."""
        if not interaction.message.embeds:
            return None
        embed = interaction.message.embeds[0]
        embed.set_footer(
            text=f"{verb} by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        return embed

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve_button(
        self, interaction: Interaction, button: discord.ui.Button
    ) -> None:
        """Record approval, keep only a disabled 'Approved' button, stop the handler's wait."""
        if not await self._claim(interaction, "approved"):
            return
        button.label = "Approved"
        button.disabled = True
        self.remove_item(self.deny_button)
        embed = self._stamp_footer(interaction, "Approved")
        kwargs = {"embed": embed} if embed is not None else {}
        await interaction.response.edit_message(view=self, **kwargs)
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(
        self, interaction: Interaction, button: discord.ui.Button
    ) -> None:
        """Record denial, keep only a disabled 'Denied' button, stop the handler's wait."""
        if not await self._claim(interaction, "denied"):
            return
        button.label = "Denied"
        button.disabled = True
        self.remove_item(self.approve_button)
        embed = self._stamp_footer(interaction, "Denied")
        kwargs = {"embed": embed} if embed is not None else {}
        await interaction.response.edit_message(view=self, **kwargs)
        self.stop()

    async def on_timeout(self) -> None:
        """Mark expired, drop the queue entry, annotate the staff message."""
        if self.decision is None:
            self.decision = "expired"
        self._disable_all()
        # message may be deleted or never attached; teardown must never raise
        if self.message is None:
            self.stop()
            return
        drop_pending(self.message.id)
        try:
            await self.message.edit(
                content="Icon request expired and was auto-rejected.", view=self
            )
        except (discord.NotFound, discord.Forbidden):
            pass
        self.stop()


def register_pending(message_id: int, role_id: int) -> None:
    """Queue keyed by staff message; resubmit replaces the role's prior entry."""
    for mid, existing in list(_PENDING.items()):
        if existing == role_id:
            del _PENDING[mid]
    _PENDING[message_id] = role_id


def drop_pending(message_id: int) -> None:
    """Remove a settled or expired queue entry, if present."""
    _PENDING.pop(message_id, None)
