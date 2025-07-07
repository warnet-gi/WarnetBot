import logging
import os
import re
from datetime import datetime, timedelta
from io import StringIO
from typing import Literal, Optional, Union

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.tcg.utils import send_missing_permission_error_embed
from bot.config import MESSAGE_LOG_CHANNEL_ID

logger = logging.getLogger(__name__)


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
                f"Synced {len(synced)} command(s) {'globally' if not spec else 'to the current guild.'}"
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

    @commands.command()
    @commands.is_owner()
    async def log(self, ctx: commands.Context, log_type: Optional[str] = 'd') -> None:
        log_dir = "bot/data/log/"
        if log_type == 'd':
            latest_log_file = max(
                (f for f in os.listdir(log_dir) if f.startswith("bot.log")),
                key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
            )
            await ctx.reply(
                file=discord.File(os.path.join(log_dir, latest_log_file), filename=latest_log_file),
                mention_author=False,
            )

        elif log_type == 'w':
            log_content = StringIO()

            log_files = sorted(
                [f for f in os.listdir(log_dir) if f.startswith("bot.log")],
                key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
            )

            for log_file in log_files:
                log_file_path = os.path.join(log_dir, log_file)
                with open(log_file_path, "r", encoding="utf-8") as f:
                    log_content.write(f.read().rstrip("\n") + "\n")

            log_content.seek(0)
            await ctx.reply(
                file=discord.File(log_content, filename="weekly.log"),
                mention_author=False,
            )
        else:
            await ctx.reply(
                "Invalid log type. Use `d` for latest log or `w` for weekly log.",
            )

    @commands.command(name='channeltopic', aliases=['ct'])
    async def channel_topic(self, ctx: commands.Context) -> None:
        if ctx.author.guild_permissions.manage_channels:
            await ctx.message.delete()

            topic: Optional[str] = None
            if isinstance(ctx.channel, discord.TextChannel):
                topic = ctx.channel.topic

            embed: discord.Embed
            if topic:
                embed = discord.Embed(
                    title=f'Channel #{ctx.channel.name}',
                    description=topic,
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title='Channel Topic Not Found',
                    description=f'**{ctx.author.name}** No topic set.',
                    color=discord.Color.red(),
                )

            await ctx.send(embed=embed)

    @app_commands.command(name='scammer', description='Ban scammer account')
    @app_commands.describe(
        user='User to be banned.',
    )
    async def give_role_on_vc(
        self,
        interaction: Interaction,
        user: Union[discord.Member, discord.User],
    ) -> None:
        await interaction.response.defer()

        if interaction.user.guild_permissions.administrator:
            try:
                await user.send(
                    "You have been banned from *WARNET | Hoyoverse Indonesia* due to being a scammer. "
                    "Please rejoin with this link: https://discord.gg/warnet"
                )
                await interaction.guild.ban(user, reason="Scammer account", delete_message_days=1)
                await interaction.guild.unban(user, reason="Scammer account")
            except Exception as e:
                logger.error(f"Unexpected error while banning {user.name}.\n {e}")
                return await interaction.followup.send(
                    content=f"An unexpected error occurred: {e}", ephemeral=True
                )

            embed = discord.Embed(
                color=discord.Color.green(),
                title='✅ User successfully banned',
                description=f"User {user.mention} has been banned from the server.",
                timestamp=datetime.now(),
            )
            embed.set_footer(
                text=f'Banned by {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url,
            )
            await interaction.followup.send(embed=embed)

        else:
            await send_missing_permission_error_embed(interaction)

    @app_commands.command(
        name='give-role-on-vc', description='Give a role to all members in a voice channel.'
    )
    @app_commands.describe(
        vc='Voice channel target.',
        role='Role that will be given to all members in voice channel target.',
    )
    async def give_role_on_vc(
        self,
        interaction: Interaction,
        vc: Union[discord.VoiceChannel, discord.StageChannel],
        role: discord.Role,
    ) -> None:
        await interaction.response.defer()

        if interaction.user.guild_permissions.manage_roles:
            cnt = 0
            for member in vc.members:
                if not member.get_role(role.id):
                    await member.add_roles(role)
                    cnt += 1

            embed = discord.Embed(
                color=discord.Color.green(),
                title='✅ Role successfully given',
                description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di channel {vc.mention}.",
                timestamp=datetime.now(),
            )
            embed.set_footer(
                text=f'Given by {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url,
            )
            await interaction.followup.send(embed=embed)

        else:
            await send_missing_permission_error_embed(interaction)

    @app_commands.command(
        name='give-role-on-poll', description='Give a role to all members who voted a poll.'
    )
    @app_commands.describe(
        role='Role that will be given to all members in voice channel target.',
        channel_poll='Channel where the poll message is located.',
        message_id='message id where poll created.',
        poll_id='Poll id that will be used to get the voters (default=1).',
    )
    async def give_role_on_poll(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel_poll: discord.TextChannel,
        message_id: app_commands.Range[str, 1],
        poll_id: Optional[int] = 1,
    ) -> None:
        await interaction.response.defer()

        try:
            poll_message = await channel_poll.fetch_message(int(message_id))
        except discord.NotFound:
            return await interaction.followup.send(
                content="Message not found in the given channel (wrong message ID).", ephemeral=True
            )

        if poll_message.poll:
            poll_answer = discord.Poll.get_answer(poll_message.poll, id=poll_id)
        else:
            return await interaction.followup.send(
                content="Poll not found in the message.", ephemeral=True
            )

        if interaction.user.guild_permissions.manage_roles:
            cnt = 0
            async for voter in poll_answer.voters():
                if not voter.get_role(role.id):
                    await voter.add_roles(role)
                    cnt += 1

            embed = discord.Embed(
                color=discord.Color.green(),
                title='✅ Role successfully given',
                description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di poll **{poll_message.poll.question}**.",
                timestamp=datetime.now(),
            )
            embed.set_footer(
                text=f'Given by {interaction.user.name}',
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
            if not message and not attachment:
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

            message_sent = await interaction.channel.send(content=message, file=file)
            await interaction.followup.send(content="Message sent!", ephemeral=True)

            log_embed = discord.Embed(
                description=(
                    f'`/admin send-message` command is triggered on {message_sent.jump_url}'
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            log_embed.set_footer(
                text=f'Triggered by {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url,
            )

            message_log_channel = interaction.guild.get_channel(MESSAGE_LOG_CHANNEL_ID)
            await message_log_channel.send(embed=log_embed)

        else:
            await interaction.response.send_message(
                content="You don't have permission to execute this command!", ephemeral=True
            )

    @commands.hybrid_group(name='schedule-message', aliases=['smsg'])
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
        *,
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

        if parsed_time := self._parse_relative_time(time):
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
                'INSERT INTO scheduled_message (guild_id, channel_id, message, date_trigger) VALUES ($1, $2, $3, $4);',
                ctx.guild.id,
                channel.id,
                message,
                date_trigger,
            )

        if self._message_schedule_task.is_running():
            self._message_schedule_task.restart()
        else:
            self._message_schedule_task.start()

        await ctx.send(
            f'⏰ Your message will be triggered in {channel.mention} <t:{int(date_trigger.timestamp())}:R>'
        )

    @schedule_message.command(name='edit', description='Edit a scheduled message.')
    @app_commands.describe(
        scheduled_message_id='Message schedule id',
        new_message='New edited message.',
    )
    async def schedule_message_edit(
        self,
        ctx: commands.Context,
        scheduled_message_id: commands.Range[int, 1],
        *,
        new_message: str,
    ) -> None:
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(
                content="❌ You don't have permission to execute this command!", ephemeral=True
            )

        async with self.db_pool.acquire() as conn:
            if await conn.fetchval(
                "SELECT id FROM scheduled_message WHERE id=$1;", scheduled_message_id
            ):
                await conn.execute(
                    'UPDATE scheduled_message SET message=$1 WHERE id=$2;',
                    new_message,
                    scheduled_message_id,
                )

            else:
                not_found_message = (
                    f'There is no scheduled message with id `{scheduled_message_id}`.\n\n'
                )
                not_found_message += 'Use `/admin schedule-message list` or `war! smsg list` to check the list of scheduled messages.'
                return await ctx.send(not_found_message)

        await ctx.send(
            f'Message is succesfully edited on scheduled message id `{scheduled_message_id}`'
        )

    @schedule_message.command(name='cancel', description='Cancel a scheduled message.')
    @app_commands.describe(scheduled_message_id='Message schedule id to be canceled.')
    async def schedule_message_cancel(
        self, ctx: commands.Context, scheduled_message_id: commands.Range[int, 1]
    ) -> None:
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(
                content="❌ You don't have permission to execute this command!", ephemeral=True
            )

        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT id FROM scheduled_message WHERE id=$1;", scheduled_message_id
            )

            if res:
                await conn.execute(
                    'DELETE FROM scheduled_message WHERE id=$1', scheduled_message_id
                )
                return await ctx.send(
                    f'Scheduled message id `{scheduled_message_id}` has been canceled.'
                )

            else:
                not_found_message = (
                    f'There is no scheduled message with id `{scheduled_message_id}`.\n\n'
                )
                not_found_message += 'Use `/admin schedule-message list` or `war! smsg list` to check the list of scheduled messages.'
                return await ctx.send(not_found_message)

    @schedule_message.command(
        name='list', description='Show the list of active scheduled messages in the guild.'
    )
    async def schedule_message_list(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(
                content="❌ You don't have permission to execute this command!", ephemeral=True
            )

        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                'SELECT * FROM scheduled_message WHERE guild_id=$1', ctx.guild.id
            )

        scheduled_message_data_list = [dict(record) for record in records]

        content = f'List of Scheduled message in **{ctx.guild.name}**\n'
        is_replied = False
        for data in scheduled_message_data_list:
            channel = ctx.guild.get_channel(data['channel_id'])
            date_trigger_unix = int(data['date_trigger'].timestamp())
            message = data['message']
            content_message = message if len(message) <= 20 else message[:20] + '...'
            content_extra = f"**{data['id']}**: {channel.mention}: {content_message} - <t:{date_trigger_unix}:F> <t:{date_trigger_unix}:R>\n"

            if len(content + content_extra) > 2000:
                if not is_replied:
                    is_replied = True
                    await ctx.reply(content=content, mention_author=False)
                else:
                    await ctx.channel.send(content=content)

                content = ''

            content += content_extra

        content += "\nCancel a message schedule by using `/admin schedule-message cancel <id>` or `war! smsg cancel <id>`"
        if is_replied:
            await ctx.channel.send(content=content)
        else:
            await ctx.reply(content=content, mention_author=False)

    @tasks.loop()
    async def _message_schedule_task(self) -> None:
        async with self.db_pool.acquire() as conn:
            next_task = await conn.fetchrow(
                'SELECT id, date_trigger FROM scheduled_message ORDER BY date_trigger LIMIT 1;'
            )

        if not next_task:
            self._message_schedule_task.stop()

        else:
            await discord.utils.sleep_until(next_task['date_trigger'])

            async with self.db_pool.acquire() as conn:
                task = await conn.fetchrow(
                    'SELECT * FROM scheduled_message WHERE id=$1;', next_task['id']
                )

            # task will be None if cancel command is triggered
            if task:
                guild = self.bot.get_guild(task['guild_id'])
                target_channel = guild.get_channel(task['channel_id'])

                if target_channel:
                    await target_channel.send(content=task['message'])

                async with self.db_pool.acquire() as conn:
                    await conn.execute('DELETE FROM scheduled_message WHERE id = $1;', task['id'])

    @_message_schedule_task.before_loop
    async def _before_message_schedule_task(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def _parse_relative_time(time_text: str) -> Optional[tuple]:
        pattern = r"\d+[dhms]"

        if matched_list := re.findall(pattern, time_text):
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
