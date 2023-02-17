import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands

from bot.config import config
from bot.bot import WarnetBot
from bot.cogs.ext.tcg.utils import send_missing_permission_error_embed

import io
import datetime, time
from typing import Optional, Literal

@commands.guild_only()
class Admin(commands.GroupCog, group_name="admin"):
    
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot

    @commands.command()
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

    @commands.command(name='channeltopic', aliases=['ct'])
    async def channel_topic(self, ctx: commands.Context) -> None:
        if ctx.author.guild_permissions.administrator or ctx.author.get_role(config.NON_ADMINISTRATOR_ROLE_ID['staff']) is not None:
            await ctx.message.delete()

            topic: Optional[str] = None
            if isinstance(ctx.channel, discord.TextChannel):
                topic = ctx.channel.topic

            embed: discord.Embed
            if topic is not None:
                embed = discord.Embed(
                    title=f'Channel #{ctx.channel.name}',
                    description=topic,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title='Channel Topic Not Found',
                    description=f'**{str(ctx.author)}** No topic set.',
                    color=discord.Color.red()
                )

            await ctx.send(embed=embed)

    @app_commands.command(name='give-role-on-vc', description='Give a role to all members in a voice channel.')
    @app_commands.describe(vc='Voice channel target.', role='Role that will be given to all members in voice channel target.')
    async def give_role_on_vc(self, interaction: Interaction, vc: discord.VoiceChannel, role: discord.Role) -> None:
        await interaction.response.defer()

        if interaction.user.guild_permissions.manage_roles:
            cnt = 0
            for member in vc.members:
                if member.get_role(role.id) is None:
                    await member.add_roles(role)
                    cnt += 1

            embed = discord.Embed(
                color=discord.Color.green(),
                title='✅ Role successfully given',
                description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di voice channel {vc.mention}.",
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(
                text=f'Given by {str(interaction.user)}',
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)

        else:
            await send_missing_permission_error_embed(interaction)

    @app_commands.command(name='send-message', description='Send message via bot.')
    @app_commands.describe(
        message='Message you want to send.',
        attachment='File to be attached on message.',
        spoiler='Set whether the attachment need to be spoilered or not.'
    )
    async def send_message(
        self, interaction: discord.Interaction,
        message: Optional[str],
        attachment: Optional[discord.Attachment],
        spoiler: Optional[bool] = False
    ) -> None:
        if interaction.user.guild_permissions.administrator:
            if message is None and attachment is None:
                return await interaction.response.send_message(content="You need to fill `message` and/or `attachment`.", ephemeral=True)
            
            await interaction.response.defer(ephemeral=True)

            message_valid = True
            file_valid = True
            if message and len(message) > 2000:
                    message_valid = False

            file: discord.File = None
            if attachment:
                if attachment.size > 8e6:  # Discord attachment size limit is 8 MB
                    file_valid = False
                else:
                    file = await attachment.to_file(spoiler=spoiler)

            if not message_valid:
                return await interaction.followup.send(content="Message failed to sent. Message can't exceed 2000 characters.", ephemeral=True)
            
            if not file_valid:
                return await interaction.followup.send(content="File failed to sent. File can't exceed 8 MB size.", ephemeral=True)

            await interaction.channel.send(content=message, file=file)
            await interaction.followup.send(content="Message sent!", ephemeral=True)

        else:
            await interaction.response.send_message(content="You don't have permission to execute this command!", ephemeral=True)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))