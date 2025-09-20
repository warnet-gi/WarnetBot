import logging
import re
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Literal

import discord
from anyio import open_file
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot import config
from bot.bot import WarnetBot
from bot.config import MESSAGE_LOG_CHANNEL_ID
from bot.helper import (
    app_guard,
    ctx_guard,
    value_is_none,
)

logger = logging.getLogger(__name__)


@commands.guild_only()
class Admin(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = self.bot.get_db_pool()

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        logger.exception("An unexpected error occurred in Admin cog", exc_info=error)
        await ctx.reply(
            "An unexpected error occurred. Please try again later.",
            delete_after=5,
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not self._message_schedule_task.is_running():
            self._message_schedule_task.start()

    @commands.command()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Literal["~", "*", "^"] | None = None,
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
    async def log(self, ctx: commands.Context, log_type: str | None = "d") -> None:
        log_dir = Path(config.LOG_DIR)
        if log_type == "d":
            latest_log_file = max(
                (f for f in log_dir.iterdir() if f.name.startswith("bot.log")),
                key=lambda f: f.stat().st_mtime,
            )
            await ctx.reply(
                file=discord.File(latest_log_file, filename=latest_log_file.name),
                mention_author=False,
            )

        elif log_type == "w":
            log_content = BytesIO()

            log_files = sorted(
                (f for f in log_dir.iterdir() if f.name.startswith("bot.log")),
                key=lambda f: f.stat().st_mtime,
            )

            for log_file in log_files:
                log_file_path = log_file
                async with await open_file(log_file_path, encoding="utf-8") as f:
                    log_content.write(
                        (await f.read()).rstrip("\n").encode("utf-8") + b"\n"
                    )

            log_content.seek(0)
            await ctx.reply(
                file=discord.File(log_content, filename="weekly.log"),
                mention_author=False,
            )

        else:
            await ctx.reply(
                "Invalid log type. Use `d` for latest log or `w` for weekly log.",
            )

    @commands.command(name="channeltopic", aliases=["ct"])
    @ctx_guard(manage_channel=True)
    async def channel_topic(self, ctx: commands.Context) -> None:
        topic: str | None = None
        if isinstance(ctx.channel, discord.TextChannel):
            topic = ctx.channel.topic

        embed: discord.Embed
        if topic:
            embed = discord.Embed(
                title=f"Channel #{ctx.channel.name}",
                description=topic,
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="Channel Topic Not Found",
                description=f"**{ctx.author.name}** No topic set.",
                color=discord.Color.red(),
            )

        await ctx.send(embed=embed)

    @app_commands.command(name="scammer", description="Ban scammer account")
    @app_commands.describe(
        user="User to be banned.",
    )
    @app_guard(admin=True)
    async def ban_scammer(
        self,
        interaction: Interaction,
        user: discord.Member | discord.User,
    ) -> None:
        if interaction.guild is None:
            return

        guild_name = interaction.guild.name
        err_msg = "DM sent successfully."
        try:
            await user.send(
                f"You have been banned from *{guild_name}* because you were identified as a scammer. "
                "You may rejoin using this link: https://discord.gg/warnet"
            )
        except Exception:  # noqa: BLE001
            err_msg = "Failed to send DM to the user. They may have DMs disabled."

        await interaction.guild.ban(
            user, reason="Scammer account", delete_message_days=1
        )
        await interaction.guild.unban(user, reason="Scammer account")
        logger.info(
            "Banned scammer",
            extra={
                "banned_id": user.id,
                "admin_id": interaction.user.id,
                "error_msg": err_msg,
            },
        )

        embed = discord.Embed(
            color=discord.Color.green(),
            title="✅ User successfully banned",
            description=f"User {user.mention} has been banned from the server. [{err_msg}]",
            timestamp=datetime.now(tz=UTC),
        )
        embed.set_footer(
            text=f"Banned by {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.followup.send(embed=embed)

        return

    @app_commands.command(
        name="give-role-on-vc",
        description="Give a role to all members in a voice channel.",
    )
    @app_commands.describe(
        vc="Voice channel target.",
        role="Role that will be given to all members in voice channel target.",
    )
    @app_guard(manage_role=True)
    async def give_role_on_vc(
        self,
        interaction: Interaction,
        vc: discord.VoiceChannel | discord.StageChannel,
        role: discord.Role,
    ) -> None:
        await interaction.response.defer()

        cnt = 0
        for member in vc.members:
            if not member.get_role(role.id):
                await member.add_roles(role)
                cnt += 1

        embed = discord.Embed(
            color=discord.Color.green(),
            title="✅ Role successfully given",
            description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di channel {vc.mention}.",
            timestamp=datetime.now(tz=UTC),
        )
        embed.set_footer(
            text=f"Given by {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )
        return await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="give-role-on-poll",
        description="Give a role to all members who voted a poll.",
    )
    @app_commands.describe(
        role="Role that will be given to all members in voice channel target.",
        channel_poll="Channel where the poll message is located.",
        message_id="message id where poll created.",
        poll_id="Poll id that will be used to get the voters (default=1).",
    )
    @app_guard(manage_role=True)
    async def give_role_on_poll(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel_poll: discord.TextChannel,
        message_id: app_commands.Range[str, 1],
        poll_id: int | None,
    ) -> None:
        await interaction.response.defer()

        if poll_id is None:
            poll_id = 1

        try:
            poll_message = await channel_poll.fetch_message(int(message_id))
        except discord.NotFound:
            return await interaction.followup.send(
                content="Message not found in the given channel (wrong message ID).",
                ephemeral=True,
            )

        if not poll_message.poll:
            return await interaction.followup.send(
                content="Poll not found in the message.", ephemeral=True
            )

        poll_answer = discord.Poll.get_answer(poll_message.poll, id=poll_id)
        if not poll_answer:
            return await interaction.followup.send(
                content="Poll answer not found in the poll.", ephemeral=True
            )

        cnt = 0
        async for voter in poll_answer.voters():
            if not voter.get_role(role.id):
                await voter.add_roles(role)
                cnt += 1

        embed = discord.Embed(
            color=discord.Color.green(),
            title="✅ Role successfully given",
            description=f"Role {role.mention} telah diberikan kepada **{cnt}** member di poll **{poll_message.poll.question}**.",
            timestamp=datetime.now(tz=UTC),
        )
        embed.set_footer(
            text=f"Given by {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )
        return await interaction.followup.send(embed=embed)

    @app_commands.command(name="send-message", description="Send message via bot.")
    @app_commands.describe(
        message="Message you want to send.",
        attachment="File to be attached on message.",
        spoiler="Set whether the attachment need to be spoilered or not.",
    )
    @app_guard(admin=True)
    async def send_message(  # noqa: C901, FIX002, PLR0912 # TODO: Improve this
        self,
        interaction: discord.Interaction,
        message: str | None,
        attachment: discord.Attachment | None,
        spoiler: bool | None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.channel:
            return None

        if spoiler is None:
            spoiler = False

        if not message and not attachment:
            await interaction.response.send_message(
                content="You need to fill `message` and/or `attachment`.",
                ephemeral=True,
            )

        message_valid = True
        file_valid = True
        max_size_msg = 2000
        if message and len(message) > max_size_msg:
            message_valid = False
        elif message:
            # support newline by typing '\n' on slash command parameter
            message = "\n".join(message.split("\\n"))

        file: discord.File | None = None
        if attachment:
            attachment_size_limit = 8e6  # Discord attachment size limit is 8 MB
            if attachment.size > attachment_size_limit:
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
                content="File failed to sent. File can't exceed 8 MB size.",
                ephemeral=True,
            )

        if file:
            message_sent = await interaction.channel.send(content=message, file=file)
        else:
            message_sent = await interaction.channel.send(content=message)
        await interaction.followup.send(content="Message sent!", ephemeral=True)

        log_embed = discord.Embed(
            description=(
                f"`/admin send-message` command is triggered on {message_sent.jump_url}"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(tz=UTC),
        )
        log_embed.set_footer(
            text=f"Triggered by {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        message_log_channel = interaction.guild.get_channel(MESSAGE_LOG_CHANNEL_ID)
        if not message_log_channel:
            return await value_is_none(value="log channel", interaction=interaction)

        await message_log_channel.send(embed=log_embed)
        return None

    @commands.hybrid_group(name="schedule-message", aliases=["smsg"])
    async def schedule_message(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @schedule_message.command(
        name="add", description="Add a message to be scheduled on a channel."
    )
    @app_commands.describe(
        channel="Channel target where the message will be sent later.",
        time="Relative time e.g. 1d, 2h, 40m, 20s, and can be combined like 5h10m20s.",
        message="Message to be scheduled.",
    )
    @ctx_guard(manage_channel=True)
    async def schedule_message_add(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel | discord.Thread | discord.ForumChannel,
        time: str,
        *,
        message: str,
    ) -> None:
        await ctx.typing()
        if not ctx.guild:
            return

        max_msg_size = 2000
        if len(message) > max_msg_size:
            await ctx.send(
                content="❌ Message failed to sent. Message can't exceed 2000 characters.",
                ephemeral=True,
            )
            return
        message = "\n".join(message.split("\\n"))  # support newline in slash command

        if parsed_time := self._parse_relative_time(time):
            day, hour, minute, second = parsed_time
        else:
            await ctx.send(
                content="❌ Wrong relative time format.",
                ephemeral=True,
            )
            return

        date_now = datetime.now(UTC)
        date_trigger = date_now + timedelta(
            days=day, hours=hour, minutes=minute, seconds=second
        )
        if date_trigger.tzinfo is None:
            date_trigger = date_trigger.replace(tzinfo=UTC)

        if date_trigger <= date_now:
            await ctx.send("❌ You must specify a time in the future.", ephemeral=True)
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO scheduled_message (guild_id, channel_id, message, date_trigger) VALUES ($1, $2, $3, $4);",
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
            f"⏰ Your message will be triggered in {channel.mention} <t:{int(date_trigger.timestamp())}:R>"
        )
        return

    @schedule_message.command(name="edit", description="Edit a scheduled message.")
    @app_commands.describe(
        scheduled_message_id="Message schedule id",
        new_message="New edited message.",
    )
    @ctx_guard(manage_channel=True)
    async def schedule_message_edit(
        self,
        ctx: commands.Context,
        scheduled_message_id: commands.Range[int, 1],
        *,
        new_message: str,
    ) -> None:
        async with self.db_pool.acquire() as conn:
            if await conn.fetchval(
                "SELECT id FROM scheduled_message WHERE id=$1;", scheduled_message_id
            ):
                await conn.execute(
                    "UPDATE scheduled_message SET message=$1 WHERE id=$2;",
                    new_message,
                    scheduled_message_id,
                )

            else:
                not_found_message = f"There is no scheduled message with id `{scheduled_message_id}`.\n\n"
                not_found_message += "Use `/admin schedule-message list` or `war! smsg list` to check the list of scheduled messages."
                await ctx.send(not_found_message)
                return

        await ctx.send(
            f"Message is succesfully edited on scheduled message id `{scheduled_message_id}`"
        )
        return

    @schedule_message.command(name="cancel", description="Cancel a scheduled message.")
    @app_commands.describe(scheduled_message_id="Message schedule id to be canceled.")
    @ctx_guard(manage_channel=True)
    async def schedule_message_cancel(
        self, ctx: commands.Context, scheduled_message_id: commands.Range[int, 1]
    ) -> None:
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT id FROM scheduled_message WHERE id=$1;", scheduled_message_id
            )

            if res:
                await conn.execute(
                    "DELETE FROM scheduled_message WHERE id=$1", scheduled_message_id
                )
                await ctx.send(
                    f"Scheduled message id `{scheduled_message_id}` has been canceled."
                )
                return

            not_found_message = (
                f"There is no scheduled message with id `{scheduled_message_id}`.\n\n"
            )
            not_found_message += "Use `/admin schedule-message list` or `war! smsg list` to check the list of scheduled messages."
            await ctx.send(not_found_message)
            return

    @schedule_message.command(
        name="list",
        description="Show the list of active scheduled messages in the guild.",
    )
    @ctx_guard(manage_channel=True)
    async def schedule_message_list(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return

        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT * FROM scheduled_message WHERE guild_id=$1", ctx.guild.id
            )

        scheduled_message_data_list = [dict(record) for record in records]

        content = f"List of Scheduled message in **{ctx.guild.name}**\n"
        is_replied = False
        max_len_msg = 20
        max_size_msg = 2000
        for data in scheduled_message_data_list:
            channel = ctx.guild.get_channel(data["channel_id"])
            if not channel:
                logger.error(
                    "Channel not found", extra={"channel_id": data["channel_id"]}
                )
                continue
            date_trigger_unix = int(data["date_trigger"].timestamp())
            message = data["message"]
            content_message = (
                message if len(message) <= max_len_msg else message[:20] + "..."
            )
            content_extra = f"**{data['id']}**: {channel.mention}: {content_message} - <t:{date_trigger_unix}:F> <t:{date_trigger_unix}:R>\n"

            if len(content + content_extra) > max_size_msg:
                if not is_replied:
                    is_replied = True
                    await ctx.reply(content=content, mention_author=False)
                else:
                    await ctx.channel.send(content=content)

                content = ""

            content += content_extra

        content += "\nCancel a message schedule by using `/admin schedule-message cancel <id>` or `war! smsg cancel <id>`"
        if is_replied:
            await ctx.channel.send(content=content)
            return

        await ctx.reply(content=content, mention_author=False)
        return

    @tasks.loop()
    async def _message_schedule_task(self) -> None:
        async with self.db_pool.acquire() as conn:
            next_task = await conn.fetchrow(
                "SELECT id, date_trigger FROM scheduled_message ORDER BY date_trigger LIMIT 1;"
            )

        if not next_task:
            self._message_schedule_task.stop()

        else:
            await discord.utils.sleep_until(next_task["date_trigger"])

            async with self.db_pool.acquire() as conn:
                task = await conn.fetchrow(
                    "SELECT * FROM scheduled_message WHERE id=$1;", next_task["id"]
                )

            # task will be None if cancel command is triggered
            if task:
                guild = self.bot.get_guild(task["guild_id"])
                if not guild:
                    logger.error(
                        "guild not found", extra={"guild_id": task["guild_id"]}
                    )
                    return
                target_channel = guild.get_channel(task["channel_id"])

                if target_channel:
                    await target_channel.send(content=task["message"])

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM scheduled_message WHERE id = $1;", task["id"]
                    )

    @_message_schedule_task.before_loop
    async def _before_message_schedule_task(self) -> None:
        await self.bot.wait_until_ready()

    @staticmethod
    def _parse_relative_time(time_text: str) -> tuple | None:
        pattern = r"\d+[dhms]"

        if matched_list := re.findall(pattern, time_text):
            day = hour = minute = second = 0
            for matched in matched_list:
                number = int(matched[:-1])

                if "d" in matched:
                    day += number
                elif "h" in matched:
                    hour += number
                elif "m" in matched:
                    minute += number
                elif "s" in matched:
                    second += number

            return day, hour, minute, second

        return None


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Admin(bot))
