from collections.abc import Callable

from discord import Interaction, app_commands
from discord.ext import commands


def app_guard(
    *,
    admin: bool = False,
    manage_channel: bool = False,
    manage_role: bool = False,
    premium: bool = False,
) -> Callable:
    async def predicate(interaction: Interaction) -> bool:
        if admin and not interaction.user.guild_permissions.administrator:
            await no_permission_alert(interaction=interaction)
            return False

        if manage_channel and not interaction.user.guild_permissions.manage_channels:
            await no_permission_alert(interaction=interaction)
            return False

        if manage_role and not interaction.user.guild_permissions.manage_roles:
            await no_permission_alert(interaction=interaction)
            return False

        if (
            premium
            and not interaction.user.premium_since
            and not interaction.user.guild_permissions.administrator
        ):
            await no_permission_alert(interaction=interaction)
            return False

        return True

    return app_commands.check(predicate)


def ctx_guard(
    *,
    admin: bool = False,
    manage_channel: bool = False,
    manage_role: bool = False,
    role_id: int | None = None,
) -> Callable:
    async def predicate(ctx: commands.Context) -> bool:
        if admin and not ctx.author.guild_permissions.administrator:
            await no_permission_alert(ctx=ctx)
            return False

        if manage_channel and not ctx.author.guild_permissions.manage_channels:
            await no_permission_alert(ctx=ctx)
            return False

        if manage_role and not ctx.author.guild_permissions.manage_roles:
            await no_permission_alert(ctx=ctx)
            return False

        if (
            role_id
            and not ctx.author.get_role(role_id)
            and not ctx.author.guild_permissions.administrator
        ):
            await no_permission_alert(ctx=ctx)
            return False

        return True

    return commands.check(predicate)


async def no_permission_alert(
    interaction: Interaction | None = None, ctx: commands.Context | None = None
) -> None:
    if ctx:
        await ctx.send("❌ This command can only be used in a guild")
    if interaction:
        await interaction.followup.send(
            "❌ You don't have permission to use this command", ephemeral=True
        )


async def value_is_none(
    value: str,
    interaction: Interaction | None = None,
    ctx: commands.Context | None = None,
) -> None:
    if ctx:
        await ctx.send(f"{value} is not found")
    if interaction:
        await interaction.followup.send(f"{value} is not found", ephemeral=True)
