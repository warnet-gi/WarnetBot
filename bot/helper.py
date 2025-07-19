from discord import Interaction
from discord.ext import commands


async def no_permission_alert(
    interaction: Interaction | None = None, ctx: commands.Context | None = None
) -> None:
    if ctx:
        await ctx.send("❌ This command can only be used in a guild")
        return None
    if interaction:
        return await interaction.followup.send(
            "❌ You don't have permission to use this command", ephemeral=True
        )
    return None


async def no_guild_alert(
    interaction: Interaction | None = None, ctx: commands.Context | None = None
) -> None:
    if ctx:
        await ctx.send("❌ This command can only be used in a guild")
        return None
    if interaction:
        return await interaction.followup.send(
            "❌ This command can only be used in a guild", ephemeral=True
        )
    return None


async def no_channel_alert(
    interaction: Interaction | None = None, ctx: commands.Context | None = None
) -> None:
    if ctx:
        await ctx.send("❌ This command can only be used in a channel")
        return None
    if interaction:
        return await interaction.followup.send(
            "❌ This command can only be used in a channel", ephemeral=True
        )
    return None


async def value_is_none(
    value: str,
    interaction: Interaction | None = None,
    ctx: commands.Context | None = None,
) -> None:
    if ctx:
        await ctx.send(f"{value} is not found")
        return None
    if interaction:
        return await interaction.followup.send(f"{value} is not found", ephemeral=True)
    return None
