from discord import Interaction
from discord.ext import commands


async def no_permission_alert(interaction: Interaction) -> None:
    return await interaction.followup.send(
        "❌ You don't have permission to use this command", ephemeral=True
    )


async def no_permission_alert_ctx(ctx: commands.Context) -> None:
    await ctx.send("❌ You don't have permission to use this command")


async def no_guild_alert(interaction: Interaction) -> None:
    return await interaction.followup.send(
        "❌ This command can only be used in a guild", ephemeral=True
    )


async def no_guild_alert_ctx(ctx: commands.Context) -> None:
    await ctx.send("❌ This command can only be used in a guild")
