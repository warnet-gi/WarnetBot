import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.ext.admin.general import admin_give_role_on_vc
from bot.cogs.ext.admin.warn import admin_warn_give

from typing import Optional, Literal, Union

@commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
class Admin(commands.GroupCog, group_name="admin"):
    """Admin commands"""

    warn = app_commands.Group(name='warn', description='Subgroup to manage Warn features.')

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.scheduler = bot.scheduler

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} command(s) {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @app_commands.command(name='give-role-on-vc', description='Give a role to all members in a voice channel.')
    @app_commands.describe(vc='Voice channel target.', role='Role that will be given to all members in voice channel target.')
    async def give_role_on_vc(self, interaction: Interaction, vc: discord.VoiceChannel, role: discord.Role) -> None:
        await admin_give_role_on_vc(self, interaction, vc, role)

    @warn.command(
        name='give',
        description='Warn and mute member based on their warn level. Will set expiration time for the warn role.'
    )
    @app_commands.describe(
        member='Member that will be given a warning.',
        warn_level='Warn level from 1 to 3.',
        reason='Reason why the warn is given.'
    )
    async def warn_give(
        self,
        interaction: Interaction,
        member: Union[discord.Member, discord.User],
        warn_level: app_commands.Range[int, 1, 3],
        reason: Optional[str]
    ) -> None:
        await admin_warn_give(self, interaction, member, warn_level, reason)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))