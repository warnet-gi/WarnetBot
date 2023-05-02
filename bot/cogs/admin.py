import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.config import config
from bot.bot import WarnetBot
from bot.cogs.ext.tcg.utils import send_missing_permission_error_embed

import re
from datetime import datetime, timedelta
from typing import Optional, Literal, Union, Tuple


WARNING_ICON_URL = 'https://cdn.discordapp.com/attachments/774322083319775262/1038314815929724989/unknown.png'


@commands.guild_only()
class Admin(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = self.bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._message_schedule_task.start()
        self._decrease_warn_status_task.start()

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
        if ctx.author.guild_permissions.manage_channels:
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
            res = await conn.fetchval(
                "SELECT id FROM scheduled_message WHERE id=$1;", scheduled_message_id
            )

            if res is not None:
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

            if res is not None:
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

        if next_task is None:
            self._message_schedule_task.stop()

        else:
            await discord.utils.sleep_until(next_task['date_trigger'])

            async with self.db_pool.acquire() as conn:
                task = await conn.fetchrow(
                    'SELECT * FROM scheduled_message WHERE id=$1;', next_task['id']
                )

            # task will be None if cancel command is triggered
            if task is not None:
                guild = self.bot.get_guild(task['guild_id'])
                target_channel = guild.get_channel(task['channel_id'])

                if target_channel is not None:
                    await target_channel.send(content=task['message'])

                async with self.db_pool.acquire() as conn:
                    await conn.execute('DELETE FROM scheduled_message WHERE id = $1;', task['id'])

    @_message_schedule_task.before_loop
    async def _before_message_schedule_task(self):
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








    warn = app_commands.Group(name='warn', description='Subgroup to manage Warn features.')

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
        interaction.response.defer()
    
        if isinstance(member, discord.User):
            return await interaction.followup.send(content=f"Can't find user with id `{member.id}` in this server.")

        scheduler: AsyncIOScheduler = self.scheduler

        async with self.db_pool.acquire() as conn:
            res = await conn.fetchrow("SELECT * FROM warned_members WHERE discord_id = $1;", member.id)
            # First time warning for a member
            if res is None:
                if warn_level > 1:
                    mute_days = [3, 7]
                    await self._mute_member(interaction, member, days=mute_days[warn_level-2], reason=f'Warn {warn_level}')

                warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{warn_level}'])
                await member.add_roles(warn_role, reason)

                date_given = datetime.now()
                date_expire = date_given + timedelta(days=30)
                await conn.execute(
                    'INSERT INTO warned_members(discord_id, warn_level, date_given, date_expire) VALUES ($1, $2, $3, $4);',
                    member.id,
                    warn_level,
                    date_given,
                    date_expire,
                )

                posix_date_expire = int(date_expire.timestamp())
                await self._send_warn_message_to_member(interaction, member, warn_level, reason, posix_date_expire)
                await self._send_warn_log(interaction, member, warn_level, reason, posix_date_expire)

            # Member has been warned before
            else:
                member_status = res
                current_warn_level = member_status['warn_level']

                if warn_level <= current_warn_level:
                    invalid_warn_notice_embed = discord.Embed(
                        title='⚠️ Warn level must be higher than the current one',
                        description=f'Tidak dapat memberikan **warn level {warn_level}** kepada user {str(member)} yang memiliki **warn level {current_warn_level}**.',
                        color=discord.Color.yellow()
                    )
                    return await interaction.followup.send(embed=invalid_warn_notice_embed)
                
                else:
                    current_warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{current_warn_level}'])
                    warn_role = interaction.guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{warn_level}'])
                    await member.remove_roles(current_warn_role)
                    await member.add_roles(warn_role, reason)

                    mute_days = [3, 7]
                    await self._mute_member(interaction, member, days=mute_days[warn_level-2], reason=f'Warn {warn_level}')

                    date_given = datetime.now()
                    date_expire = date_given + timedelta(days=30)
                    await conn.execute(
                        "UPDATE warned_members SET warn_level=$1, date_given=$2, date_expire=$3, leave_server=0 WHERE discord_id=$4;",
                        warn_level,
                        date_given,
                        date_expire,
                        member.id
                    )

                    posix_date_expire = int(date_expire.timestamp())
                    await self._send_warn_message_to_member(interaction, member, warn_level, reason, posix_date_expire)
                    await self._send_warn_log(interaction, member, warn_level, reason, posix_date_expire)
        
        # TODO: Add scheduler to check the warn status
        scheduler.add_job(decrease_warn_status, trigger='date', args=[self, member], id=f'decrease_warn-{str(member)}', replace_existing=True, run_date=date_expire)

    # alur: cek status warn terkiini -> kurangi level warn
        # jika warn 1 menjadi 0, maka hapus entry
        # jika warn 3 menjadi 2 atau warn 2 menjadi 1, maka update entry -> add job lagi
    # TODO edge case: member keluar server setelah kena warn sampai job pengecekan datang
    # TODO edge case: member keluar server setelah kena warn lalu kembali lagi sebelum job pengecekan datang
    @tasks.loop()
    async def _decrease_warn_status_task(self) -> None:
        async with self.db_pool.acquire() as conn:
            next_task = await conn.fetchrow(
                'SELECT discord_id, date_expire FROM warned_members ORDER BY date_expire LIMIT 1;'
            )

        if next_task is None:
            return self._decrease_warn_status_task.stop()

        else:
            await discord.utils.sleep_until(next_task['date_expire'])

            async with self.db_pool.acquire() as conn:
                task = await conn.fetchrow(
                    'SELECT * FROM warned_members WHERE discord_id=$1;', next_task['discord_id']
                )

            if task is not None:
                guild = self.bot.get_guild(config.GUILD_ID)
                member = guild.get_member(task['discord_id'])
                current_warn_level: int = task['warn_level']
                current_warn_role = guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{current_warn_level}'])
                

                is_leave_server = False
                if not member:  # if the member leaves the server
                    is_leave_server = True
                else:
                    await member.remove_roles(current_warn_role)

                # Decrease warn level
                async with self.db_pool.acquire() as conn:
                    if current_warn_level > 1:
                        next_warn_level = current_warn_level - 1
                        next_warn_role = guild.get_role(config.WarnConfig.WARN_ROLE_ID[f'warn{next_warn_level}'])
                        await member.add_roles(next_warn_role)

                        date_given = datetime.now()
                        date_expire = date_given + timedelta(days=30)
                        
                        await conn.execute(
                            "UPDATE warned_members SET warn_level=$1, date_given=$2, date_expire=$3, leave_server='0' WHERE discord_id=$4;",
                            next_warn_level,
                            date_given,
                            date_expire,
                            member.id
                        )

                    # TODO: send log when the warn level decreased

                    # No warn anymore
                    else:
                        await conn.execute("DELETE FROM warned_members WHERE discord_id=$1;", member.id)

    @_decrease_warn_status_task.before_loop
    async def _before_decrease_warn_status_task(self):
        await self.bot.wait_until_ready()

    @staticmethod
    async def _send_warn_message_to_member(
        interaction: Interaction,
        member: discord.Member,
        warn_level: int,
        reason: Optional[str],
        expiration_date: int  # POSIX time
    ) -> None:
        """DM member for the warning."""
        
        dm_channel: discord.DMChannel = member.create_dm()
        author = interaction.user

        warning_embed = discord.Embed(
            title="⚠️ You got a warning!",
            description="Admin/Mod telah memberikan peringatan kepadamu.",
            color=discord.Color.yellow(),
            timestamp=datetime.now(),
        )
        warning_embed.set_thumbnail(url=WARNING_ICON_URL)
        warning_embed.add_field(name='Warn Level', value=f'`{warn_level}`', inline=False)
        warning_embed.add_field(
            name='Reason',
            value=reason if reason is not None else '-',
            inline=False
        )
        warning_embed.add_field(
            name='Warning Expiration Time',
            value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
            inline=False
        )
        warning_embed.set_footer(
            text=f'Warned by {str(author)}',
            icon_url=author.display_avatar.url
        )

        await dm_channel.send(embed=warning_embed)

    @staticmethod
    async def _send_warn_log(
        interaction: Interaction,
        member: discord.Member,
        warn_level: int,
        reason: Optional[str],
        expiration_date: int  # POSIX time
    ) -> None:
        """Log every warning action."""

        author = interaction.user

        log_embed = discord.Embed(
            title='Member has been warned',
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name='Warn Level', value=f'`{warn_level}`', inline=False)
        log_embed.add_field(
            name='Reason',
            value=reason if reason is not None else '-',
            inline=False
        )
        log_embed.add_field(
            name='Warning Expiration Time',
            value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
            inline=False
        )
        log_embed.set_footer(
            text=f'Warned by {str(author)}',
            icon_url=author.display_avatar.url
        )
        warn_log_channel = interaction.guild.get_channel(config.WarnConfig.WARN_LOG_CHANNEL_ID)
        await warn_log_channel.send(embed=log_embed)

    async def _mute_member(
        self,
        interaction: Interaction,
        member: discord.Member,
        days: Optional[int],
        reason: str
    ) -> None:
        muted_role = interaction.guild.get_role(config.WarnConfig.MUTED_ROLE_ID)
        booster_role = interaction.guild.get_role(config.BOOSTER_ROLE_ID)
        member_role_id_list = [role.id for role in member.roles]

        if member.get_role(config.BOOSTER_ROLE_ID):
            await member.edit(roles=[booster_role])
        else:
            await member.edit(roles=[])    
        await member.add_roles(muted_role)

        date_given = datetime.now()
        date_expire = date_given + timedelta(days=days)

        async with self.db_pool.acquire as conn:
            await conn.execute(
                "INSERT INTO muted_members(discord_id, date_given, date_expire, reason, roles_store) VALUES ($1, $2, $3, $4, $5);",
                member.id,
                date_given,
                date_expire,
                reason,
                member_role_id_list
            )

        posix_date_expire = int(date_expire.timestamp())
        await self._send_mute_message_to_member(member, reason, posix_date_expire)

        if self._unmute_member_task.is_running():
            self._unmute_member_task.restart()
        else:
            self._unmute_member_task.start()

    # TODO: handle when member leave
    @tasks.loop()
    async def _unmute_member_task(self) -> None:
        async with self.db_pool.acquire() as conn:
            next_task = await conn.fetchrow(
                'SELECT discord_id, date_expire FROM muted_members WHERE leave_server=FALSE ORDER BY date_expire LIMIT 1;'
            )
        
        if next_task is None:
            return self._decrease_warn_status_task.stop()

        else:
            await discord.utils.sleep_until(next_task['date_expire'])

            async with self.db_pool.acquire() as conn:
                task = await conn.fetchrow(
                    'SELECT * FROM muted_members WHERE discord_id=$1;', next_task['discord_id']
                )

                if task is not None:
                    guild = self.bot.get_guild(config.GUILD_ID)
                    member = guild.get_member(task['discord_id'])
                    muted_role = guild.get_role(config.WarnConfig.MUTED_ROLE_ID)

                    is_leave_server = False
                    if not member:  # if the member leaves the server
                        is_leave_server = True
                        await conn.execute(
                            "UPDATE muted_members SET leave_server=$1 WHERE discord_id=$2;",
                            is_leave_server,
                            member.id,
                        )
                    else:
                        roles_stored = task['roles_store']
                        role_list = []
                        for role_id in roles_stored:
                            role = guild.get_role(role_id)
                            if role:
                                role_list.append(role)
                        await member.remove_roles(muted_role)
                        await member.edit(roles=role_list)
                        await conn.execute("DELETE FROM muted_members WHERE discord_id=$1;", member.id)

    @_unmute_member_task.before_loop
    async def _before_unmute_member_task(self):
        await self.bot.wait_until_ready()

    @staticmethod
    async def _send_mute_message_to_member(
        member: discord.Member,
        reason: Optional[str],
        expiration_date: int  # POSIX time
    ) -> None:
        """DM member for the mute action."""
        
        dm_channel: discord.DMChannel = member.create_dm()

        mute_embed = discord.Embed(
            title="⚠️ You have been muted!",
            description="Admin/Mod telah memberikan mute kepadamu.",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )
        mute_embed.set_thumbnail(url=WARNING_ICON_URL)
        mute_embed.add_field(
            name='Reason',
            value=reason if reason is not None else '-',
            inline=False
        )
        mute_embed.add_field(
            name='Mute Expiration Time',
            value=f"<t:{expiration_date}:F>, <t:{expiration_date}:R>",
            inline=False
        )

        await dm_channel.send(embed=mute_embed)

        @staticmethod
        async def send_missing_permission_error_embed(interaction: Interaction, custom_description: str = None) -> None:
            description = f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini."
            if custom_description:
                description = custom_description

            embed = discord.Embed(
                color=discord.Colour.red(),
                title="❌ You don't have permission",
                description=description,
                timestamp=datetime.now(),
            )

            await interaction.followup.send(embed=embed)




async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))
