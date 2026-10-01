# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalOperand=false, reportArgumentType=false, reportCallIssue=false
import asyncio
import io
import logging

import asyncpg
import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot import config
from bot.bot import WarnetBot
from bot.cogs.ext.color.utils import generate_image_color_list
from bot.cogs.views.color import (
    CustomRoleFormView,
    IconApprovalView,
    drop_pending,
    register_pending,
)
from bot.cogs.views.confirm import ConfirmView
from bot.config import CustomRoleConfig

logger = logging.getLogger(__name__)

_MAX_ICON_KB = 256
_MAX_ICON_BYTES = _MAX_ICON_KB * 1024
_ICON_CONTENT_TYPES = ("image/png", "image/jpeg")
_NUMBERED_ROLES_SQL = "SELECT *, ROW_NUMBER() OVER (ORDER BY created_at, role_id) AS n FROM custom_roles WHERE guild_id = $1"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Stored colors are "#rrggbb" (str(discord.Colour)); split into an RGB tuple."""
    text = value.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _swatch_url(primary: str, secondary: str | None) -> str:
    """Flat-color (or gradient) preview image for an embed thumbnail; hex args have no leading '#'."""
    if secondary is None:
        return f"https://placehold.co/200x200/{primary}/{primary}.png"
    return (
        "https://fpoimg.com/200x200?text=%20&text_color=ffffff&dims=false"
        f"&gradient={primary},{secondary}&gradient_angle=90"
    )


def _help_embeds(
    m: dict[str, str], prefix: str, color: discord.Colour
) -> list[discord.Embed]:
    """Two embeds: how the system works, then one field per command (m maps subcommand -> clickable mention)."""
    overview = discord.Embed(
        title="💎 Booster custom roles",
        description=(
            "Server boosters can have a personal role with their own name and color, or wear a role another "
            "booster made. Every role is public: any booster can wear it.\n"
            "### The rules\n"
            "• You can **own one** role (the one you create) and **wear one** role at a time.\n"
            "• Owning lasts until you delete the role; wearing is just what shows on your profile.\n"
            f"• The server holds up to **{CustomRoleConfig.CUSTOM_ROLE_LIMIT}** custom roles.\n"
            "• If you stop boosting, the role is taken off you automatically. Your own role is **kept**, "
            "not deleted, and you can wear it again once you boost again.\n"
            "• If staff rename, recolor or delete a custom role in server settings, the bot picks it up by itself."
        ),
        color=color,
    )
    overview.add_field(
        name="🚀 New here? Start with these",
        value=(
            f"1. {m['list']} to see every role and its **number**\n"
            f"2. {m['use']} with a number to wear one, **or**\n"
            f"3. {m['create']} to make your own"
        ),
        inline=False,
    )

    commands_embed = discord.Embed(title="📚 Commands", color=color)
    fields = (
        (
            "✨ Create your role",
            (
                f"{m['create']}\n"
                "Pick **Single color** or **Gradient color**, then fill in the form: a role name and a hex color "
                "such as `#FF0000` (gradients ask for a second hex). The role is made, placed in the booster section "
                "and put on you, and the server sees an announcement.\n"
                "*Needs: you are boosting, you don't own or wear a custom role yet, and the server has a free slot.*"
            ),
        ),
        (
            "🎨 Change your role",
            (
                f"{m['edit']}\n"
                "Owner only. Choose to change the **name**, the **color**, or **both**. Colors can switch between "
                "single and gradient. Everyone wearing the role sees the change and the server sees an announcement."
            ),
        ),
        (
            "🖼 Add an icon",
            (
                f"{m['icon']}\n"
                f"Owner only. Attach a **PNG or JPEG up to {_MAX_ICON_KB}KB**. Staff get a request with "
                "**Approve / Deny** buttons and have **15 minutes** to answer. Approved icons are applied "
                "automatically. If it is denied or nobody answers, nothing changes and you can submit again "
                "(a new request replaces the old one).\n"
                "*The server must have role icons unlocked.*"
            ),
        ),
        (
            "📋 Browse all roles",
            (
                f"{m['list']}\n"
                "Posts a picture of every custom role: **number**, name and color. Numbers follow the order roles "
                "were created and **shift down when an earlier role is deleted**, so check the list right before "
                "using a number. Names longer than 20 characters are shortened in the picture only."
            ),
        ),
        (
            "🏷 Wear a role",
            (
                f"{m['use']} `number`\n"
                "Wears the role with that number from the list. If you already wear one it is **swapped** "
                "automatically. Owners can wear someone else's role too; their own role stays theirs and can be worn "
                "again the same way. The server sees an announcement. An unknown number is refused."
            ),
        ),
        (
            "👋 Take a role off",
            (
                f"{m['discard']}\n"
                "Stops you wearing your current role. Nothing is deleted, and if it is your own role "
                "you keep ownership."
            ),
        ),
        (
            "🗑 Delete a role",
            (
                f"{m['delete']}\n"
                "Deletes **your own** role for everyone who wears it. You must confirm first, and it "
                "**cannot be undone**, and the server sees an announcement. Staff with *Manage Roles* can add "
                "a `number` to delete any role; everyone else who tries that is refused."
            ),
        ),
        (
            "🔍 Look up a role",
            (
                f"{m['info']} `number` (optional)\n"
                "Shows the owner, how many people wear it, its colors and when it was created. Leave the number "
                "out to see your own role (the one you wear, otherwise the one you own). Only you see the answer."
            ),
        ),
        (
            "🔌 Staff only: force a resync",
            (
                f"`{prefix}colorsync` (aliases `{prefix}custom_role_sync`, `{prefix}cr_sync`)\n"
                "Needs *Manage Roles*. Compares the bot's records with the real roles: drops roles that no longer "
                "exist, refreshes names and colors, and clears members who no longer have the role. Use it if "
                "something looks out of date."
            ),
        ),
    )
    for name, value in fields:
        commands_embed.add_field(name=name, value=value, inline=False)
    return [overview, commands_embed]


async def _require_booster(interaction: Interaction) -> discord.Member | None:
    """Allow only active boosters; ephemeral-refuse and return None otherwise."""
    user = interaction.user
    if isinstance(user, discord.Member) and user.premium_since is not None:
        return user
    embed = discord.Embed(
        description="Only server boosters can use custom roles.",
        color=discord.Color.red(),
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    return None


@commands.guild_only()
class CustomRole(commands.GroupCog, group_name="warnet-color"):
    """Self-serve booster custom roles: one owned or joined role per booster."""

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self._backfill_done = False
        self._list_image_cache: dict[int, bytes] = {}
        self._list_versions: dict[int, int] = {}
        self._group_command_id: int | None = None

    def _invalidate_list_image(self, guild_id: int) -> None:
        """Drop the cached list image and bump the version so an in-flight render is not stored."""
        self._list_image_cache.pop(guild_id, None)
        self._list_versions[guild_id] = self._list_versions.get(guild_id, 0) + 1

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """Unwear (never delete) the role the moment premium lapses."""
        if before.premium_since is None or after.premium_since is not None:
            return
        try:
            stripped = await self._strip_worn(after.guild, after.id)
        except Exception:
            logger.exception("Boost-loss strip failed", extra={"user_id": after.id})
            return
        if stripped:
            logger.info(
                "Stripped custom role on boost loss", extra={"user_id": after.id}
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """A leaver must not stay 'wearing' a role: it would block create/use after they rejoin."""
        try:
            await self._strip_worn(member.guild, member.id)
        except Exception:
            logger.exception("Leave strip failed", extra={"user_id": member.id})

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # on_ready fires on every reconnect; backfill once
        """One-time backfill for downtime: strip lapsed boosters, clear leavers."""
        if self._backfill_done:
            return
        self._backfill_done = True
        for guild in self.bot.guilds:
            try:
                await self._backfill_guild(guild)
            except Exception:
                # one failing guild must not skip the rest, and _backfill_done is already set
                logger.exception(
                    "Custom-role backfill failed", extra={"guild_id": guild.id}
                )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """Staff deleting a tracked role via server settings must cascade out of the DB too."""
        async with self.db_pool.acquire() as conn:
            tag = await conn.execute(
                "DELETE FROM custom_roles WHERE role_id = $1;", role.id
            )
        if tag != "DELETE 0":
            self._invalidate_list_image(role.guild.id)
            logger.info(
                "Custom role deleted manually, DB synced",
                extra={"guild_id": role.guild.id, "role_id": role.id},
            )

    @commands.Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        """Staff renaming/recoloring a tracked role via server settings must mirror into the DB."""
        unchanged = (
            before.name == after.name
            and before.colour == after.colour
            and before.secondary_colour == after.secondary_colour
        )
        if unchanged:
            return
        style = "gradient" if after.secondary_colour is not None else "single"
        async with self.db_pool.acquire() as conn:
            tag = await conn.execute(
                "UPDATE custom_roles SET name = $1, style = $2, primary_color = $3, secondary_color = $4 "
                "WHERE role_id = $5;",
                after.name,
                style,
                str(after.colour),
                str(after.secondary_colour)
                if after.secondary_colour is not None
                else None,
                after.id,
            )
        if tag != "UPDATE 0":
            self._invalidate_list_image(after.guild.id)
            logger.info(
                "Custom role edited manually, DB synced",
                extra={"guild_id": after.guild.id, "role_id": after.id},
            )

    async def _unwear(
        self,
        guild: discord.Guild,
        user_id: int,
        worn: asyncpg.Record,
        reason: str,
    ) -> bool:
        """Remove a worn custom role from Discord, then its membership row; False if Discord refused."""
        member = guild.get_member(user_id)
        role = guild.get_role(worn["role_id"])
        if member is not None and role is not None:
            try:
                await member.remove_roles(role, reason=reason)
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Custom role removal failed",
                    extra={"user_id": user_id, "role_id": role.id},
                )
                return False
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM custom_role_members WHERE role_id = $1 AND user_id = $2;",
                worn["role_id"],
                user_id,
            )
        return True

    async def _strip_worn(self, guild: discord.Guild, user_id: int) -> bool:
        """Boost lost or member left: unwear whatever they wear; ownership is never touched."""
        worn = await self._worn_role(guild.id, user_id)
        if worn is None:
            return False
        return await self._unwear(guild, user_id, worn, "Server boost ended")

    async def _backfill_guild(self, guild: discord.Guild) -> None:
        """Sweep one guild's member rows; ownership rows are never touched."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT m.role_id, m.user_id FROM custom_role_members m "
                "JOIN custom_roles r ON r.role_id = m.role_id WHERE r.guild_id = $1;",
                guild.id,
            )
        stripped = 0
        cleared = 0
        for row in rows:
            member = guild.get_member(row["user_id"])
            if member is None or member.premium_since is None:
                # left server -> auto-leave; lost boost -> unwear; ownership never touched
                # the row already names the role, no need to look the membership up again
                if await self._unwear(guild, row["user_id"], row, "Server boost ended"):
                    if member is None:
                        cleared += 1
                    else:
                        stripped += 1
        if stripped or cleared:
            logger.info(
                "Custom-role backfill done",
                extra={"guild_id": guild.id, "stripped": stripped, "cleared": cleared},
            )

    async def _worn_role(self, guild_id: int, user_id: int) -> asyncpg.Record | None:
        """Role row the user currently wears in this guild, if any."""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT r.* FROM custom_role_members m "
                "JOIN custom_roles r ON r.role_id = m.role_id "
                "WHERE m.user_id = $1 AND r.guild_id = $2;",
                user_id,
                guild_id,
            )

    async def _owned_role(self, guild_id: int, user_id: int) -> asyncpg.Record | None:
        """Role row the user owns in this guild, if any."""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM custom_roles WHERE guild_id = $1 AND owner_id = $2;",
                guild_id,
                user_id,
            )

    async def _has_active_role(self, guild_id: int, user_id: int) -> bool:
        """One-role rule: worn or owned counts as active."""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM custom_role_members m JOIN custom_roles r ON r.role_id = m.role_id "
                "WHERE m.user_id = $2 AND r.guild_id = $1) "
                "OR EXISTS(SELECT 1 FROM custom_roles WHERE guild_id = $1 AND owner_id = $2);",
                guild_id,
                user_id,
            )

    async def _delete_discord_role(
        self, role: discord.Role | None, actor: discord.Member
    ) -> str | None:
        """Delete the Discord role (Discord strips it from every wearer itself); error text on failure."""
        if role is None:
            return None
        try:
            await role.delete(reason=f"Custom role deleted by {actor} ({actor.id})")
        except discord.NotFound:
            pass  # already gone; the caller still cascades the DB rows
        except (discord.Forbidden, discord.HTTPException):
            return "Could not delete the Discord role (permissions)."
        return None

    async def _rollback_role(self, role: discord.Role, reason: str) -> None:
        """Best-effort delete of a half-created Discord role; the DB rows (if any) follow via on_guild_role_delete."""
        try:
            await role.delete(reason=f"{reason}, rolling back")
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Rollback could not delete the role", extra={"role_id": role.id}
            )

    async def _finalize_create(
        self,
        guild: discord.Guild,
        member: discord.Member,
        anchor: discord.Role,
        form: dict,
        new_role: discord.Role,
    ) -> tuple[str | None, str | None]:
        """Position, persist, then grant; returns (fatal_error, warning) and rolls the role back on a fatal error."""
        try:
            # guild.roles may not yet include new_role (ROLE_CREATE gateway event is async and
            # can lag the create_role() HTTP response), so Role.edit(position=...) can compute a
            # stale no-op reorder. edit_role_positions sends positions directly instead — and since
            # the target slot is likely already held by an earlier custom role, every role between
            # the target and the anchor is shifted down by one in the same bulk request.
            target = max(anchor.position - 1, 1)
            positions: dict[discord.Role, int] = {new_role: target}
            for existing in guild.roles:
                if existing.id in (anchor.id, new_role.id):
                    continue
                if target <= existing.position < anchor.position:
                    positions[existing] = existing.position - 1
            await guild.edit_role_positions(
                positions, reason="Position under booster anchor"
            )
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO custom_roles"
                    "(role_id, guild_id, owner_id, name, style, primary_color, secondary_color) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7);",
                    new_role.id,
                    guild.id,
                    member.id,
                    form["name"],
                    form["style"],
                    str(form["primary"]),
                    str(form["secondary"]) if form["secondary"] is not None else None,
                )
                await conn.execute(
                    "INSERT INTO custom_role_members (role_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;",
                    new_role.id,
                    member.id,
                )
        except asyncpg.UniqueViolationError:
            await self._rollback_role(new_role, "Owner already has a custom role")
            return (
                "You are already in a custom role. Use /warnet-color discard first.",
                None,
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.exception("Custom role setup failed", extra={"guild_id": guild.id})
            await self._rollback_role(new_role, "Custom role setup failed")
            return (
                "Could not finish role setup (permissions). The bot role must sit above the anchor role.",
                None,
            )
        except Exception:
            logger.exception(
                "Custom role DB write failed", extra={"guild_id": guild.id}
            )
            await self._rollback_role(new_role, "Custom role DB write failed")
            return "Could not save the role. Try again later.", None
        self._invalidate_list_image(guild.id)
        try:
            await member.add_roles(new_role, reason="Custom role created")
        except (discord.Forbidden, discord.HTTPException):
            # keep the DB honest: they own the role but are not wearing it yet
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM custom_role_members WHERE role_id = $1 AND user_id = $2;",
                    new_role.id,
                    member.id,
                )
            return (
                None,
                "I could not grant you the new role (permissions). Use /warnet-color use to wear it.",
            )
        return None, None

    async def _run_form(
        self,
        interaction: Interaction,
        member: discord.Member,
        mode: str,
        current: dict | None = None,
    ) -> dict | None:
        """Show the ComponentsV2 form and wait; None means the user timed out."""
        view = CustomRoleFormView(member, mode=mode, current=current)
        await interaction.response.send_message(view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()
        return view.result

    async def _announce_saved(
        self,
        interaction: Interaction,
        guild: discord.Guild,
        member: discord.Member,
        form: dict,
        role: discord.Role,
        verb: str,
    ) -> None:
        """Delete the prompt message, then announce once, publicly, in the role color."""
        if verb == "created":
            title = "Custom role created!"
            sentence = f"{member.mention} just created the custom role {role.mention}!"
        else:
            what = {"name": "name", "colors": "colors"}.get(
                form.get("scope") or "both", "name and colors"
            )
            title = "Custom role updated!"
            sentence = f"{member.mention} just updated the {what} of {role.mention}!"
        embed = discord.Embed(title=title, description=sentence, color=form["primary"])
        embed.add_field(name="Style", value=form["style"])
        primary_hex = f"{form['primary'].value:06X}"
        colors = f"#{primary_hex}"
        secondary_hex = None
        if form["style"] == "gradient" and form["secondary"] is not None:
            secondary_hex = f"{form['secondary'].value:06X}"
            colors += f" \u2192 #{secondary_hex}"
        embed.set_thumbnail(url=_swatch_url(primary_hex, secondary_hex))
        embed.add_field(name="Colors", value=colors)
        try:
            form_message = await interaction.original_response()
            await form_message.delete()
        except (discord.NotFound, discord.HTTPException):
            pass
        channel = interaction.channel
        if channel is not None:
            try:
                await channel.send(embed=embed)
                return
            except (discord.Forbidden, discord.HTTPException):
                logger.warning("Save announcement failed", extra={"guild_id": guild.id})
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _create_blocker(
        self, guild: discord.Guild, member: discord.Member
    ) -> str | None:
        """Reason this member cannot create a role right now (cap reached / already in one), else None."""
        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM custom_roles WHERE guild_id = $1;", guild.id
            )
        if total >= CustomRoleConfig.CUSTOM_ROLE_LIMIT:
            return f"Custom-role limit reached ({CustomRoleConfig.CUSTOM_ROLE_LIMIT}). Use /warnet-color list to join one."
        if await self._has_active_role(guild.id, member.id):
            return "You are already in a custom role. Use /warnet-color discard first."
        return None

    @app_commands.command(
        name="create", description="Create a custom booster role (name + color)."
    )
    async def create_role(self, interaction: Interaction) -> None:
        """Gate (booster, cap, one-role, anchor), form, re-gate, create, position, persist, grant."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        blocker = await self._create_blocker(guild, member)
        if blocker is not None:
            await interaction.response.send_message(blocker, ephemeral=True)
            return
        anchor = guild.get_role(CustomRoleConfig.ANCHOR_ROLE_ID)
        if anchor is None:
            await interaction.response.send_message(
                "Custom roles are not configured yet (anchor role missing).",
                ephemeral=True,
            )
            return
        form = await self._run_form(interaction, member, "create")
        if form is None:
            return
        # the form can stay open for minutes: another create (or a second form of theirs) may have won the race
        blocker = await self._create_blocker(guild, member)
        if blocker is not None:
            await interaction.followup.send(blocker, ephemeral=True)
            return
        create_kwargs: dict = {}
        if form["style"] == "gradient":
            create_kwargs["secondary_color"] = form["secondary"]
        try:
            new_role = await guild.create_role(
                name=form["name"],
                colour=form["primary"],
                reason=f"Custom role created by {member} ({member.id})",
                **create_kwargs,
            )
        except discord.HTTPException as exc:
            logger.exception(
                "Custom role create failed",
                extra={"guild_id": guild.id, "status": exc.status, "code": exc.code},
            )
            await interaction.followup.send(
                f"Could not create the role: {exc.text or exc}",
                ephemeral=True,
            )
            return
        error, warning = await self._finalize_create(
            guild, member, anchor, form, new_role
        )
        if error is not None:
            await interaction.followup.send(error, ephemeral=True)
            return
        await self._announce_saved(
            interaction, guild, member, form, new_role, "created"
        )
        if warning is not None:
            await interaction.followup.send(warning, ephemeral=True)

    @app_commands.command(
        name="edit", description="Edit your owned custom role (name + color)."
    )
    async def edit_role(self, interaction: Interaction) -> None:
        """Owner-only rename/recolor; explicit None clears a gradient to single."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        owned = await self._owned_role(guild.id, member.id)
        if owned is None:
            await interaction.response.send_message(
                "You do not own a custom role.", ephemeral=True
            )
            return
        role = guild.get_role(owned["role_id"])
        if role is None:
            await interaction.response.send_message(
                "Your Discord role no longer exists. Use /warnet-color delete to clean up.",
                ephemeral=True,
            )
            return
        current = {
            "name": owned["name"],
            "style": owned["style"],
            "primary": owned["primary_color"],
            "secondary": owned["secondary_color"],
        }
        form = await self._run_form(interaction, member, "edit", current=current)
        if form is None:
            return
        try:
            # MISSING-sentinel defaults: explicit None clears the gradient.
            await role.edit(
                name=form["name"],
                colour=form["primary"],
                secondary_color=form["secondary"]
                if form["style"] == "gradient"
                else None,
                reason=f"Custom role edited by {member} ({member.id})",
            )
        except discord.Forbidden:
            logger.exception("Custom role edit failed", extra={"role_id": role.id})
            await interaction.followup.send(
                "Could not edit the role (permissions).", ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            logger.exception(
                "Custom role edit failed",
                extra={"role_id": role.id, "status": exc.status, "code": exc.code},
            )
            await interaction.followup.send(
                f"Could not edit the role: {exc.text or exc}", ephemeral=True
            )
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE custom_roles SET name = $1, style = $2, primary_color = $3, secondary_color = $4 "
                "WHERE role_id = $5;",
                form["name"],
                form["style"],
                str(form["primary"]),
                str(form["secondary"]) if form["secondary"] is not None else None,
                role.id,
            )
        self._invalidate_list_image(guild.id)
        await self._announce_saved(interaction, guild, member, form, role, "updated")

    @app_commands.command(
        name="icon", description="Request an icon for your owned custom role."
    )
    @app_commands.describe(
        image=f"Role icon image (max {_MAX_ICON_KB}KB). Goes to staff for approval."
    )
    async def request_icon(
        self, interaction: Interaction, image: discord.Attachment
    ) -> None:
        """Owner uploads art; staff message pings every approver role, 15m expiry."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        if "ROLE_ICONS" not in guild.features:
            await interaction.response.send_message(
                "This server has not unlocked role icons.", ephemeral=True
            )
            return
        if image.content_type not in _ICON_CONTENT_TYPES:
            await interaction.response.send_message(
                "Icon must be a PNG or JPEG image.", ephemeral=True
            )
            return
        if image.size > _MAX_ICON_BYTES:
            await interaction.response.send_message(
                f"Image must be {_MAX_ICON_KB}KB or smaller.", ephemeral=True
            )
            return
        owned = await self._owned_role(guild.id, member.id)
        if owned is None:
            await interaction.response.send_message(
                "You do not own a custom role.", ephemeral=True
            )
            return
        role = guild.get_role(owned["role_id"])
        if role is None:
            await interaction.response.send_message(
                "Your Discord role no longer exists.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        data = await image.read()
        channel = interaction.channel
        if channel is None:
            await interaction.followup.send(
                "Could not find the channel for the staff request.", ephemeral=True
            )
            return
        staff_ids = list(CustomRoleConfig.STAFF_ROLE_IDS)
        view = IconApprovalView(
            role_id=role.id, owner_id=member.id, staff_role_ids=staff_ids
        )
        embed = discord.Embed(
            title="Custom role icon request",
            description=f"Role {role.mention} requested by {member.mention}",
            color=role.colour,
        )
        embed.set_image(url=image.url)
        try:
            mentions = " ".join(f"<@&{rid}>" for rid in staff_ids)
            msg = await channel.send(content=mentions, embed=embed, view=view)  # type: ignore[arg-type]
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(
                "Could not post the staff request (permissions).", ephemeral=True
            )
            return
        view.message = msg
        register_pending(msg.id, role.id)
        await interaction.followup.send(
            "Icon submitted! Staff will review it within 15 minutes.",
            ephemeral=True,
        )
        await view.wait()
        drop_pending(msg.id)
        await self._resolve_icon_decision(interaction, role, member, data, view)

    async def _resolve_icon_decision(
        self,
        interaction: Interaction,
        role: discord.Role,
        member: discord.Member,
        data: bytes,
        view: IconApprovalView,
    ) -> None:
        """Apply an approval from request_icon's view.wait().

        Denial and expiry need no reply: the staff message already shows the outcome (footer/disabled button).
        """
        if view.decision != "approved":
            return
        try:
            await role.edit(
                display_icon=data, reason=f"Icon approved for {member} ({member.id})"
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.exception(
                "Applying approved icon failed", extra={"role_id": role.id}
            )
            try:
                await interaction.followup.send(
                    "Staff approved, but applying the icon failed.", ephemeral=True
                )
            except discord.HTTPException:
                pass  # the interaction token (15 min) may already be gone after a long review

    async def _numbered_role(self, guild_id: int, number: int) -> asyncpg.Record | None:
        """Resolve a list-displayed number to its role row; numbers shift as roles are deleted."""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow(
                f"SELECT * FROM ({_NUMBERED_ROLES_SQL}) t WHERE n = $2;",
                guild_id,
                number,
            )

    @app_commands.command(name="list", description="Browse joinable custom roles.")
    async def list_roles(self, interaction: Interaction) -> None:
        """Numbered role image, refreshed on create/edit/delete and cached otherwise."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        await interaction.response.defer()
        image = self._list_image_cache.get(guild.id)
        if image is None:
            version = self._list_versions.get(guild.id, 0)
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(f"{_NUMBERED_ROLES_SQL} ORDER BY n;", guild.id)
            roles = [(row["name"], _hex_to_rgb(row["primary_color"])) for row in rows]
            try:
                # Pillow drawing: keep off the event loop.
                image = await asyncio.to_thread(
                    lambda: generate_image_color_list(roles).getvalue()
                )
            except Exception:
                logger.exception(
                    "Custom role list render failed", extra={"guild_id": guild.id}
                )
                await interaction.followup.send(
                    "Could not render the role list. Try again later.", ephemeral=True
                )
                return
            # a create/edit/delete during the render made this image stale; serve it once, don't cache it
            if self._list_versions.get(guild.id, 0) == version:
                self._list_image_cache[guild.id] = image
        embed = discord.Embed(color=member.color)
        embed.set_footer(text=f"Custom roles in {guild.name}")
        embed.set_image(url="attachment://warnet-colors.png")
        await interaction.followup.send(
            embed=embed,
            file=discord.File(io.BytesIO(image), filename="warnet-colors.png"),
        )

    @app_commands.command(
        name="use",
        description="Join an existing custom role by its /warnet-color list number.",
    )
    @app_commands.describe(number="Role number shown in /warnet-color list.")
    async def use_role(
        self, interaction: Interaction, number: app_commands.Range[int, 1]
    ) -> None:
        """Wear a tracked role, swapping out whatever role the user currently wears."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        target = await self._numbered_role(guild.id, number)
        if target is None:
            await interaction.response.send_message(
                f"No custom role numbered {number}.", ephemeral=True
            )
            return
        role = guild.get_role(target["role_id"])
        if role is None:
            await interaction.response.send_message(
                "That role no longer exists on Discord.", ephemeral=True
            )
            return
        worn = await self._worn_role(guild.id, member.id)
        if worn is not None and worn["role_id"] == role.id:
            await interaction.response.send_message(
                "You are already wearing this role.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        # grant first so a failed grant never leaves the member with nothing
        try:
            await member.add_roles(role, reason=f"Joined custom role ({member.id})")
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(
                "Could not grant the role (permissions).", ephemeral=True
            )
            return
        if worn is not None and not await self._unwear(
            guild, member.id, worn, "Swapped custom role"
        ):
            try:
                await member.remove_roles(role, reason="Swap failed, reverting")
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Swap revert failed",
                    extra={"user_id": member.id, "role_id": role.id},
                )
            await interaction.followup.send(
                "Could not remove your current role (permissions).", ephemeral=True
            )
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO custom_role_members (role_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;",
                role.id,
                member.id,
            )
        await interaction.followup.send(
            f"You are now wearing {role.mention}!", ephemeral=True
        )
        embed = discord.Embed(
            title="Custom role joined!",
            description=f"{member.mention} joined the custom role {role.mention}.",
            color=role.colour,
        )
        await self._post_public(interaction, embed, "Join")

    @app_commands.command(name="discard", description="Leave your current custom role.")
    async def discard_role(self, interaction: Interaction) -> None:
        """Unwear only; ownership persists."""
        member = await _require_booster(interaction)
        guild = interaction.guild
        if member is None or guild is None:
            return
        worn = await self._worn_role(guild.id, member.id)
        if worn is None:
            await interaction.response.send_message(
                "You are not wearing a custom role.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        if not await self._unwear(guild, member.id, worn, "Left custom role"):
            await interaction.followup.send(
                "Could not remove the role (permissions).", ephemeral=True
            )
            return
        # Ownership persists: discarding only unwears, never deletes or transfers.
        await interaction.followup.send("You left the custom role.", ephemeral=True)

    async def _post_public(
        self, interaction: Interaction, embed: discord.Embed, what: str
    ) -> None:
        """Post an announcement in the channel the command ran in; a failed post is only logged."""
        channel = interaction.channel
        if channel is None:
            return
        try:
            await channel.send(embed=embed)  # type: ignore[union-attr]
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "%s announcement failed", what, extra={"guild_id": interaction.guild_id}
            )

    async def _announce_deleted(
        self,
        interaction: Interaction,
        actor: discord.Member,
        record: asyncpg.Record,
        color: discord.Colour,
    ) -> None:
        """Tell the channel a custom role is gone, in the role's last color."""
        sentence = f"{actor.mention} deleted the custom role **{record['name']}**"
        if record["owner_id"] is not None and actor.id != record["owner_id"]:
            sentence += f" owned by <@{record['owner_id']}>"
        embed = discord.Embed(
            title="Custom role deleted!", description=f"{sentence}.", color=color
        )
        await self._post_public(interaction, embed, "Delete")

    async def _resolve_delete_target(
        self,
        guild: discord.Guild,
        member: discord.Member,
        staff: bool,
        number: int | None,
    ) -> tuple[asyncpg.Record | None, str | None]:
        """Owner path resolves the owned row; staff may name any tracked role by its list number."""
        if number is None:
            record = await self._owned_role(guild.id, member.id)
            if record is None:
                hint = (
                    "You do not own a custom role. Staff: pass a number to delete a specific role."
                    if staff
                    else "You do not own a custom role."
                )
                return None, hint
            return record, None
        if not staff:
            return None, "Only staff can delete a specific role."
        record = await self._numbered_role(guild.id, number)
        if record is None:
            return None, f"No custom role numbered {number}."
        return record, None

    @app_commands.command(
        name="delete", description="Delete a custom role entirely (owner or staff)."
    )
    @app_commands.describe(
        number="Staff only: role number from /warnet-color list, instead of your own."
    )
    async def delete_role(
        self, interaction: Interaction, number: app_commands.Range[int, 1] | None = None
    ) -> None:
        """Owner deletes own role; staff (manage_roles) may delete any tracked role."""
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return
        staff = member.guild_permissions.manage_roles
        if not staff:
            boosted = await _require_booster(interaction)
            if boosted is None:
                return
            member = boosted
        record, error = await self._resolve_delete_target(guild, member, staff, number)
        if error is not None:
            await interaction.response.send_message(error, ephemeral=True)
            return
        target = guild.get_role(record["role_id"])
        await interaction.response.defer(ephemeral=True)
        view = ConfirmView(member)
        msg = await interaction.followup.send(
            embed=discord.Embed(
                title="Delete custom role?",
                description=f"This deletes **{record['name']}** for everyone wearing it. This cannot be undone.",
                color=discord.Color.red(),
            ),
            view=view,
            wait=True,
        )
        view.message = msg
        await view.wait()
        if not view.confirmed:
            cancelled = discord.Embed(
                title="Delete cancelled",
                description="Timed out waiting for confirmation."
                if view.confirmed is None
                else "Role kept.",
                color=discord.Color.orange(),
            )
            try:
                await msg.edit(embed=cancelled, view=None)
            except discord.NotFound:
                await interaction.followup.send(embed=cancelled, ephemeral=True)
            return
        async with self.db_pool.acquire() as conn:
            # count first: on_guild_role_delete may cascade the rows away the moment Discord deletes the role
            wearers = await conn.fetchval(
                "SELECT COUNT(*) FROM custom_role_members WHERE role_id = $1;",
                record["role_id"],
            )
        color = target.colour if target is not None else discord.Colour.default()
        delete_error = await self._delete_discord_role(target, member)
        if delete_error is not None:
            await interaction.followup.send(delete_error, ephemeral=True)
            return
        async with self.db_pool.acquire() as conn:
            # members cascade from the role row
            await conn.execute(
                "DELETE FROM custom_roles WHERE role_id = $1;", record["role_id"]
            )
        self._invalidate_list_image(guild.id)
        logger.info(
            "Custom role deleted",
            extra={
                "guild_id": guild.id,
                "role_id": record["role_id"],
                "owner_id": record["owner_id"],
                "actor_id": member.id,
                "staff": staff,
            },
        )
        note = (
            " (removed by staff)" if staff and record["owner_id"] != member.id else ""
        )
        result = discord.Embed(
            title="Custom role deleted",
            description=f"**{record['name']}** removed from **{wearers}** member(s).{note}",
            color=discord.Color.green(),
        )
        try:
            await msg.edit(embed=result, view=None)
        except discord.NotFound:
            await interaction.followup.send(embed=result, ephemeral=True)
        await self._announce_deleted(interaction, member, record, color)

    @app_commands.command(name="info", description="Show warnet-color details.")
    @app_commands.describe(
        number="Optional: role number from /warnet-color list. Defaults to your own role."
    )
    async def role_info(
        self, interaction: Interaction, number: app_commands.Range[int, 1] | None = None
    ) -> None:
        """No number: worn role first, owned fallback. With a number: that role, whoever owns it."""
        guild = interaction.guild
        if guild is None:
            return
        if number is None:
            user_id = interaction.user.id
            record = await self._worn_role(guild.id, user_id) or await self._owned_role(
                guild.id, user_id
            )
            if record is None:
                await interaction.response.send_message(
                    "You are not in a custom role.", ephemeral=True
                )
                return
        else:
            record = await self._numbered_role(guild.id, number)
            if record is None:
                await interaction.response.send_message(
                    f"No custom role numbered {number}.", ephemeral=True
                )
                return
        role = guild.get_role(record["role_id"])
        title = role.mention if role is not None else record["name"]
        async with self.db_pool.acquire() as conn:
            member_count = await conn.fetchval(
                "SELECT COUNT(*) FROM custom_role_members WHERE role_id = $1;",
                record["role_id"],
            )
        primary = record["primary_color"]
        secondary = record["secondary_color"] if record["style"] == "gradient" else None
        colors = primary or "—"
        if secondary:
            colors += f" → {secondary}"
        embed = discord.Embed(
            title=f"Custom role: {record['name']}",
            color=role.color if role is not None else discord.Color.default(),
        )
        if primary:
            embed.set_thumbnail(
                url=_swatch_url(
                    primary.lstrip("#"), secondary.lstrip("#") if secondary else None
                )
            )
        owner = f"<@{record['owner_id']}>" if record["owner_id"] is not None else "none"
        embed.description = (
            f"{title}\nOwner: {owner}\nMembers: **{member_count}**\n"
            f"Style: {record['style']} ({colors})\nCreated: {record['created_at']:%Y-%m-%d}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="colorsync", aliases=["custom_role_sync", "cr_sync"])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def custom_role_sync(self, ctx: commands.Context) -> None:
        """Manual backup for the on_guild_role_* listeners: reconcile DB rows against live Discord state."""
        guild = ctx.guild
        if guild is None:
            return
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM custom_roles WHERE guild_id = $1;", guild.id
            )
            member_rows = await conn.fetch(
                "SELECT m.role_id, m.user_id FROM custom_role_members m "
                "JOIN custom_roles r ON r.role_id = m.role_id WHERE r.guild_id = $1;",
                guild.id,
            )
            removed = 0
            updated = 0
            stale: list[tuple[int, int]] = []
            for row in rows:
                role = guild.get_role(row["role_id"])
                if role is None:
                    await conn.execute(
                        "DELETE FROM custom_roles WHERE role_id = $1;", row["role_id"]
                    )
                    removed += 1
                    continue
                style = "gradient" if role.secondary_colour is not None else "single"
                primary = str(role.colour)
                secondary = (
                    str(role.secondary_colour)
                    if role.secondary_colour is not None
                    else None
                )
                if (
                    role.name != row["name"]
                    or style != row["style"]
                    or primary != row["primary_color"]
                    or (secondary != row["secondary_color"])
                ):
                    await conn.execute(
                        "UPDATE custom_roles SET name = $1, style = $2, primary_color = $3, secondary_color = $4 "
                        "WHERE role_id = $5;",
                        role.name,
                        style,
                        primary,
                        secondary,
                        role.id,
                    )
                    updated += 1
            live_ids = {
                row["role_id"]
                for row in rows
                if guild.get_role(row["role_id"]) is not None
            }
            for member_row in member_rows:
                if member_row["role_id"] not in live_ids:
                    continue  # role row was just deleted above; members cascade
                member = guild.get_member(member_row["user_id"])
                if member is None or member.get_role(member_row["role_id"]) is None:
                    stale.append((member_row["role_id"], member_row["user_id"]))
            if stale:
                await conn.executemany(
                    "DELETE FROM custom_role_members WHERE role_id = $1 AND user_id = $2;",
                    stale,
                )
            stale_members = len(stale)
        if removed or updated:
            self._invalidate_list_image(guild.id)
        logger.info(
            "Custom role manual sync done",
            extra={
                "guild_id": guild.id,
                "removed": removed,
                "updated": updated,
                "stale_members": stale_members,
            },
        )
        await ctx.send(
            f"Sync complete: **{removed}** role(s) removed, **{updated}** updated, "
            f"**{stale_members}** stale membership(s) cleared.",
        )

    @commands.command(name="colorbackfill")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def color_backfill(self, ctx: commands.Context) -> None:
        """One-time step after bot/data/migrations/001_custom_role_v2.sql; safe to run again."""
        guild = ctx.guild
        if guild is None:
            return
        await ctx.typing()
        async with self.db_pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "UPDATE custom_roles SET guild_id = $1 WHERE guild_id IS NULL;",
                guild.id,
            )
            rows = await conn.fetch(
                "SELECT role_id, name FROM custom_roles WHERE guild_id = $1 ORDER BY created_at, role_id;",
                guild.id,
            )
            removed = filled = wearers = skipped = 0
            seen: set[int] = set()  # one worn role per user: the oldest role wins
            for row in rows:
                role = guild.get_role(row["role_id"])
                if role is None:
                    await conn.execute(
                        "DELETE FROM custom_roles WHERE role_id = $1;", row["role_id"]
                    )
                    removed += 1
                    continue
                secondary = role.secondary_colour
                await conn.execute(
                    "UPDATE custom_roles SET name = $1, style = $2, primary_color = $3, secondary_color = $4 "
                    "WHERE role_id = $5;",
                    role.name,
                    "gradient" if secondary is not None else "single",
                    str(role.colour),
                    str(secondary) if secondary is not None else None,
                    role.id,
                )
                filled += 1
                for member in role.members:
                    if member.id in seen:
                        skipped += 1
                        continue
                    seen.add(member.id)
                    await conn.execute(
                        "INSERT INTO custom_role_members (role_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;",
                        role.id,
                        member.id,
                    )
                    wearers += 1
            # every row is now filled: lock the schema to the final shape
            await conn.execute(
                "ALTER TABLE custom_roles ALTER COLUMN guild_id SET NOT NULL, ALTER COLUMN name SET NOT NULL;"
            )
        self._invalidate_list_image(guild.id)
        logger.info(
            "Custom role backfill done",
            extra={
                "guild_id": guild.id,
                "filled": filled,
                "removed": removed,
                "wearers": wearers,
                "skipped": skipped,
            },
        )
        await ctx.reply(
            f"Backfill complete: **{filled}** role(s) filled, **{removed}** missing role(s) dropped, "
            f"**{wearers}** wearer(s) recorded, **{skipped}** extra wearer(s) skipped.",
            mention_author=False,
        )

    async def _command_mention(self, guild: discord.Guild, subcommand: str) -> str:
        """Clickable </warnet-color sub:id> mention; falls back to plain text if lookup fails."""
        if self._group_command_id is None:
            try:
                commands_ = await self.bot.tree.fetch_commands(guild=guild)
                if not commands_:
                    commands_ = await self.bot.tree.fetch_commands()
            except discord.HTTPException:
                commands_ = []
            found = discord.utils.get(commands_, name="warnet-color")
            if found is not None:
                self._group_command_id = found.id
        if self._group_command_id is None:
            return f"`/warnet-color {subcommand}`"
        return f"</warnet-color {subcommand}:{self._group_command_id}>"

    @app_commands.command(
        name="help", description="How custom roles work, command by command."
    )
    async def role_help(self, interaction: Interaction) -> None:
        """Explain the rules and every command, with clickable slash-command mentions."""
        guild = interaction.guild
        if guild is None:
            return
        await interaction.response.defer(ephemeral=True)
        m = {
            sub: await self._command_mention(guild, sub)
            for sub in (
                "create",
                "edit",
                "icon",
                "list",
                "use",
                "discard",
                "delete",
                "info",
            )
        }
        embeds = _help_embeds(m, config.BOT_PREFIX[0], interaction.user.color)
        await interaction.followup.send(embeds=embeds, ephemeral=True)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(CustomRole(bot))
