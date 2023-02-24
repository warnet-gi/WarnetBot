import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.config import config
from bot.bot import WarnetBot
from bot.cogs.ext.tcg.utils import send_missing_permission_error_embed

import re
from datetime import datetime, timedelta
from typing import Optional, Literal, Union, Tuple


@commands.guild_only()
class Admin(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = self.bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._message_schedule_task.start()

    @commands.command()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
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
        if (
            ctx.author.guild_permissions.administrator
            or ctx.author.get_role(config.NON_ADMINISTRATOR_ROLE_ID['staff']) is not None
        ):
            await ctx.message.delete()

            topic: Optional[str] = None
            if isinstance(ctx.channel, discord.TextChannel):
                topic = ctx.channel.topic

            embed: discord.Embed
            if topic is not None:
                embed = discord.Embed(
                    title=f'Channel #{ctx.channel.name}',
                    description=topic,
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title='Channel Topic Not Found',
                    description=f'**{str(ctx.author)}** No topic set.',
                    color=discord.Color.red(),
                )

            await ctx.send(embed=embed)

    @app_commands.command(
        name='give-role-on-vc', description='Give a role to all members in a voice channel.'
    )
    @app_commands.describe(
        vc='Voice channel target.',
        role='Role that will be given to all members in voice channel target.',
    )
    async def give_role_on_vc(
        self, interaction: Interaction, vc: discord.VoiceChannel, role: discord.Role
    ) -> None:
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
                timestamp=datetime.now(),
            )
            embed.set_footer(
                text=f'Given by {str(interaction.user)}',
                icon_url=interaction.user.display_avatar.url,
            )
            await interaction.followup.send(embed=embed)

        else:
            await send_missing_permission_error_embed(interaction)

    @app_commands.command(name='send-message', description='Send message via bot.')
    @app_commands.describe(
        message='Message you want to send.',
        attachment='File to be attached on message.',
        spoiler='Set whether the attachment need to be spoilered or not.',
    )
    async def send_message(
        self,
        interaction: discord.Interaction,
        message: Optional[str],
        attachment: Optional[discord.Attachment],
        spoiler: Optional[bool] = False,
    ) -> None:
        if interaction.user.guild_permissions.administrator:
            if message is None and attachment is None:
                return await interaction.response.send_message(
                    content="You need to fill `message` and/or `attachment`.", ephemeral=True
                )

            await interaction.response.defer(ephemeral=True)

            message_valid = True
            file_valid = True
            if message and len(message) > 2000:
                message_valid = False
            elif message:
                # support newline by typing '\n' on slash command parameter
                message = '\n'.join(message.split('\\n'))

            file: discord.File = None
            if attachment:
                if attachment.size > 8e6:  # Discord attachment size limit is 8 MB
                    file_valid = False
                else:
                    file = await attachment.to_file(spoiler=spoiler)

            if not message_valid:
                return await interaction.followup.send(
                    content="Message failed to sent. Message can't exceed 2000 characters.",
                    ephemeral=True,
                )

            if not file_valid:
                return await interaction.followup.send(
                    content="File failed to sent. File can't exceed 8 MB size.", ephemeral=True
                )

            await interaction.channel.send(content=message, file=file)
            await interaction.followup.send(content="Message sent!", ephemeral=True)

        else:
            await interaction.response.send_message(
                content="You don't have permission to execute this command!", ephemeral=True
            )

    @commands.hybrid_group()
    async def schedule_message(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @schedule_message.command(name='add', description='Add a message to be scheduled on a channel.')
    @app_commands.describe(
        channel='Channel target where the message will be sent later.',
        time='Relative time e.g. 1d, 2h, 40m, 20s, and can be combined like 5h10m20s.',
        message='Message to be scheduled.',
    )
    async def schedule_message_add(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.Thread, discord.ForumChannel],
        time: str,
        message: str,
    ) -> None:
        await ctx.typing()
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(
                content="❌ You don't have permission to execute this command!", ephemeral=True
            )

        if len(message) > 2000:
            return await ctx.send(
                content="❌ Message failed to sent. Message can't exceed 2000 characters.",
                ephemeral=True,
            )
        message = '\n'.join(message.split('\\n'))  # support newline in slash command

        parsed_time = self._parse_relative_time(time)
        if parsed_time is not None:
            day, hour, minute, second = parsed_time
        else:
            return await ctx.send(
                content="❌ Wrong relative time format.",
                ephemeral=True,
            )

        date_now = datetime.now()
        date_trigger = date_now + timedelta(days=day, hours=hour, minutes=minute, seconds=second)

        if date_trigger <= date_now:
            return await ctx.send('❌ You must specify a time in the future.', ephemeral=True)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO scheduled_message (channel_id, message, date_trigger) VALUES ($1, $2, $3);',
                channel.id,
                message,
                date_trigger,
            )

        if self._message_schedule_task.is_running():
            self._message_schedule_task.restart()
            print('restart loop')
        else:
            self._message_schedule_task.start()
            print('start loop')

        await ctx.send(
            f'⏰ Your message will be triggered in {channel.mention} <t:{int(date_trigger.timestamp())}:R>'
        )

    @tasks.loop()
    async def _message_schedule_task(self) -> None:
        async with self.db_pool.acquire() as conn:
            next_task = await conn.fetchrow(
                'SELECT * FROM scheduled_message ORDER BY date_trigger LIMIT 1;'
            )

        if next_task is None:
            self._message_schedule_task.stop()

        else:
            await discord.utils.sleep_until(next_task['date_trigger'])

            guild = self.bot.get_guild(config.GUILD_ID)
            target_channel = guild.get_channel(next_task['channel_id'])

            await target_channel.send(content=next_task['message'])

            async with self.db_pool.acquire() as conn:
                next_task = await conn.execute(
                    'DELETE FROM scheduled_message WHERE id = $1;', next_task['id']
                )

    @_message_schedule_task.before_loop
    async def _before_message_schedule_task(self):
        print('waiting for the bot ready...')
        await self.bot.wait_until_ready()

    @staticmethod
    def _parse_relative_time(time_text: str) -> Optional[Tuple]:
        pattern = r"\d+[dhms]"
        matched_list = re.findall(pattern, time_text)

        if matched_list:
            day = hour = minute = second = 0
            for matched in matched_list:
                number = int(matched[:-1])

                if 'd' in matched:
                    day += number
                elif 'h' in matched:
                    hour += number
                elif 'm' in matched:
                    minute += number
                elif 's' in matched:
                    second += number

            return day, hour, minute, second

        else:
            return


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))
