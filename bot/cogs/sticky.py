# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalOperand=false, reportArgumentType=false, reportCallIssue=false
import asyncio
import contextlib
import logging
from datetime import UTC, datetime

import asyncpg
import discord
from discord import AllowedMentions, Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.views.confirm import ConfirmView
from bot.cogs.views.sticky import StickyPagination

logger = logging.getLogger(__name__)


@commands.guild_only()
class Sticky(commands.GroupCog, group_name="sticky"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.sticky_data: dict[int, list] = {}
        self.no_mention = AllowedMentions(
            everyone=False,
            users=False,
            roles=False,
            replied_user=False,
        )
        self._locks: dict[int, asyncio.Lock] = {}
        self._bg_tasks: set[asyncio.Task] = set()
        self._pending: dict[int, asyncio.Task] = {}
        self._gen: dict[int, int] = {}
        self._loaded = False
        self._load_lock = asyncio.Lock()

    async def cog_load(self) -> None:
        # runs on startup AND on reload; on_connect never re-fires after a cog reload
        await self._load_cache()

    async def _load_cache(self) -> None:
        """Fill sticky_data from the DB. On failure, on_message retries on the next message."""
        async with self._load_lock:
            if self._loaded:
                return
            try:
                async with self.db_pool.acquire() as conn:
                    records = await conn.fetch(
                        "SELECT * FROM sticky ORDER BY channel_id ASC;"
                    )
            except (asyncpg.PostgresError, OSError, TimeoutError):
                logger.exception("Sticky cache load failed; retrying on next message")
                return
            for data in records:
                # setdefault: never clobber an entry a command wrote while we were loading
                self.sticky_data.setdefault(
                    data["channel_id"],
                    [data["message_id"], data["message"], data["delay_time"]],
                )
            self._loaded = True
            logger.info("Sticky cache loaded", extra={"count": len(records)})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return
        if not self._loaded:
            await self._load_cache()
        cid = message.channel.id
        if cid not in self.sticky_data:
            return
        # generation counter: a repost already in flight loops once more if this bumps it
        self._gen[cid] = self._gen.get(cid, 0) + 1
        if cid in self._pending:
            return
        task = asyncio.create_task(self._repost_sticky(message.channel))
        self._pending[cid] = task
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _repost_sticky(self, channel: discord.abc.Messageable) -> None:
        """One task per channel: debounce, repost, and repeat if messages landed during the repost."""
        cid = channel.id
        try:
            while True:
                current = self.sticky_data.get(cid)
                if current is None:
                    return
                await asyncio.sleep(current[2])
                seen = self._gen.get(cid, 0)
                async with self._locks.setdefault(cid, asyncio.Lock()):
                    await self._repost_once(channel)
                if self._gen.get(cid, 0) == seen:
                    return
        finally:
            self._pending.pop(cid, None)

    async def _repost_once(self, channel: discord.abc.Messageable) -> None:
        """Rotate the sticky to the bottom. Caller holds the channel lock."""
        try:
            current = self.sticky_data.get(channel.id)
            if current is None:
                return
            sticky_id, sticky_msg = current[0], current[1]

            prev, sticky_msg = await self._fetch_prev_or_reseed(
                channel, sticky_id, sticky_msg
            )
            if prev is None:
                return

            # Send new sticky BEFORE deleting old one so a send failure
            # does not leave the channel with no sticky and a dangling DB row.
            try:
                msg = await channel.send(sticky_msg, allowed_mentions=self.no_mention)
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Sticky send failed",
                    extra={"channel_id": getattr(channel, "id", "?")},
                )
                return

            try:
                await prev.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Sticky delete failed",
                    extra={"channel_id": getattr(channel, "id", "?")},
                )

            if channel.id not in self.sticky_data:
                # removed/purged while we were sending; do not resurrect the row
                with contextlib.suppress(discord.HTTPException):
                    await msg.delete()
                return
            await self._upsert_sticky(channel.id, msg.id, sticky_msg, current[2])
            self.sticky_data[channel.id] = [msg.id, sticky_msg, current[2]]

        except Exception:
            logger.exception(
                "Unexpected sticky repost error",
                extra={"channel_id": getattr(channel, "id", "?")},
            )

    async def _reseed_sticky(
        self, channel: discord.abc.Messageable, current: list
    ) -> None:
        """Re-send a missing sticky and upsert its new id. Never deletes the row."""
        try:
            msg = await channel.send(current[1], allowed_mentions=self.no_mention)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Sticky reseed failed",
                extra={"channel_id": getattr(channel, "id", "?")},
            )
            return
        await self._upsert_sticky(channel.id, msg.id, current[1], current[2])
        self.sticky_data[channel.id] = [msg.id, current[1], current[2]]

    async def _fetch_prev_or_reseed(
        self,
        channel: discord.abc.Messageable,
        sticky_id: int,
        sticky_msg: str,
    ) -> tuple[discord.Message | None, str]:
        """Fetch previous sticky; (None, msg) means the caller must return."""
        # never DELETE the row on a single 404. A transient API
        # hiccup or a concurrent rotate winning the race would destroy the
        # sticky while a live message still exists. Confirm, then re-seed.
        try:
            prev = await channel.fetch_message(sticky_id)
        except discord.NotFound:
            pass
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Sticky fetch failed", extra={"channel_id": getattr(channel, "id", "?")}
            )
            return None, sticky_msg
        else:
            return prev, sticky_msg
        cur = self.sticky_data.get(channel.id)
        if cur is None or cur[0] != sticky_id:
            return None, sticky_msg  # removed/rotated concurrently
        await asyncio.sleep(2)  # ride out transient 404s
        cur = self.sticky_data.get(channel.id)
        if cur is None or cur[0] != sticky_id:
            return None, sticky_msg
        try:
            prev = await channel.fetch_message(sticky_id)
        except discord.NotFound:
            await self._reseed_sticky(channel, cur)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Sticky fetch failed", extra={"channel_id": getattr(channel, "id", "?")}
            )
        else:
            return prev, cur[1]
        return None, sticky_msg

    async def _upsert_sticky(
        self, channel_id: int, message_id: int, message: str, delay_time: int
    ) -> None:
        # Upsert (not bare UPDATE) so a missing row heals instead of updating 0 rows.
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO sticky (channel_id, message_id, message, delay_time) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (channel_id) DO UPDATE SET message_id=$2, message=$3, delay_time=$4;",
                channel_id,
                message_id,
                message,
                delay_time,
            )

    async def cog_unload(self) -> None:
        for t in list(self._bg_tasks):
            t.cancel()

    @app_commands.command(name="list", description="List channel with sticky message.")
    async def list_sticky_messages(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        async with self.db_pool.acquire() as conn:
            res = await conn.fetch("SELECT * FROM sticky ORDER BY channel_id ASC;")
            record = [dict(row) for row in res]

            view = StickyPagination(list_data=record)
            await view.start(interaction)

    @app_commands.command(name="add", description="Add sticky message to a channel.")
    @app_commands.describe(
        message="Sticky message.",
        channel="Target channel.",
        delay_time="Delay after new message is sent on a channel (in seconds). Default is 2 seconds.",
    )
    async def add_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 1, 2000],
        channel: discord.TextChannel | discord.Thread,
        delay_time: app_commands.Range[int, 2, 1800] | None,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetchrow(
                    "SELECT channel_id FROM sticky WHERE channel_id=$1;",
                    channel.id,
                )

            target = interaction.guild.get_channel_or_thread(channel.id)
            instance_name = (
                "thread" if isinstance(target, discord.Thread) else "channel"
            )
            if not res:
                message = "\n".join(message.split("\\n"))
                msg = await target.send(message, allowed_mentions=self.no_mention)
                if not delay_time:
                    delay_time = 2  # default value

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO sticky (channel_id,message_id,message,delay_time) VALUES ($1,$2,$3,$4);",
                        channel.id,
                        msg.id,
                        message,
                        delay_time,
                    )

                self.sticky_data[channel.id] = [msg.id, message, delay_time]
                logger.info(
                    "NEW STICKY MESSSAGE HAS BEEN ADDED",
                    extra={"channel_id": channel.id},
                )

                await self._send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message successfully given",
                    description=(
                        f"Berhasil menambahkan sticky message pada {instance_name} {channel.mention}\n"
                        f"**Message**: {message}\n"
                        f"**Delay time**: `{delay_time} secs`"
                    ),
                )

            else:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message already exist",
                    description=f"Sticky message telah terpasang pada {instance_name} {channel.mention}",
                )

        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Create Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(name="edit", description="Edit sticky message.")
    @app_commands.describe(
        message="New sticky message.",
        channel="Channel name.",
        delay_time="New delay time after new message is sent on a channel (in seconds).",
    )
    async def edit_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 1, 2000],
        channel: discord.TextChannel | discord.Thread,
        delay_time: app_commands.Range[int, 2, 1800] | None,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    "SELECT channel_id, message_id, delay_time FROM sticky WHERE channel_id=$1;",
                    channel.id,
                )

            target = interaction.guild.get_channel_or_thread(channel.id)
            instance_name = (
                "thread" if isinstance(target, discord.Thread) else "channel"
            )
            if not data:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
                )
            else:
                if not delay_time:
                    delay_time = data["delay_time"]

                message = "\n".join(message.split("\\n"))
                async with self._locks.setdefault(channel.id, asyncio.Lock()):
                    try:
                        sticky_msg = await channel.fetch_message(data["message_id"])
                        sticky_data = await sticky_msg.edit(content=message)
                    except discord.errors.NotFound:
                        sticky_channel = interaction.guild.get_channel_or_thread(
                            channel.id
                        )
                        sticky_data = await sticky_channel.send(
                            message, allowed_mentions=self.no_mention
                        )

                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE sticky SET message=$2, delay_time=$3, message_id=$4 WHERE channel_id=$1;",
                            channel.id,
                            message,
                            delay_time,
                            sticky_data.id,
                        )

                    self.sticky_data[channel.id] = [sticky_data.id, message, delay_time]

                await self._send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message update successfully",
                    description=(
                        f"Berhasil memperbarui sticky message pada {instance_name} {channel.mention}\n"
                        f"**New message**: {message}\n"
                        f"**Delay time**: `{delay_time} secs`"
                    ),
                )
        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Edit Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(
        name="remove", description="Remove sticky message from channel."
    )
    @app_commands.describe(channel="Target channel.")
    async def remove_sticky_message(
        self,
        interaction: Interaction,
        channel: discord.TextChannel | discord.Thread,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    "SELECT channel_id,message_id FROM sticky WHERE channel_id=$1;",
                    channel.id,
                )

            target = interaction.guild.get_channel_or_thread(channel.id)
            instance_name = (
                "thread" if isinstance(target, discord.Thread) else "channel"
            )
            if not data:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
                )
            else:
                # lock: an in-flight repost must not re-insert the row we are deleting
                async with self._locks.setdefault(channel.id, asyncio.Lock()):
                    try:
                        sticky = await channel.fetch_message(data["message_id"])
                        await sticky.delete()
                    except discord.errors.NotFound:
                        pass

                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "DELETE FROM sticky WHERE channel_id=$1;", channel.id
                        )

                    self.sticky_data.pop(channel.id, None)
                logger.info(
                    "NEW STICKY MESSSAGE HAS BEEN REMOVED",
                    extra={"channel_id": channel.id},
                )

                await self._send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message removed successfully",
                    description=f"Berhasil menghapus sticky message pada {instance_name} {channel.mention}",
                )
        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(
        name="resend", description="Resend sticky message to channels."
    )
    @app_commands.describe(channel="Target Channel")
    async def resend_sticky_message(
        self,
        interaction: Interaction,
        channel: discord.TextChannel | discord.Thread,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    "SELECT * FROM sticky WHERE channel_id=$1;",
                    channel.id,
                )

            target = interaction.guild.get_channel_or_thread(channel.id)
            instance_name = (
                "thread" if isinstance(target, discord.Thread) else "channel"
            )
            if not data:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
                )
            else:
                async with self._locks.setdefault(channel.id, asyncio.Lock()):
                    try:
                        existing = await channel.fetch_message(data["message_id"])
                    except discord.errors.NotFound:
                        existing = None
                    # send before deleting so a send failure keeps the old sticky in place
                    msg = await target.send(
                        data["message"], allowed_mentions=self.no_mention
                    )
                    if existing is not None:
                        try:
                            await existing.delete()
                        except (
                            discord.NotFound,
                            discord.Forbidden,
                            discord.HTTPException,
                        ):
                            logger.warning(
                                "Sticky delete failed", extra={"channel_id": channel.id}
                            )
                    await self._upsert_sticky(
                        channel.id, msg.id, data["message"], data["delay_time"]
                    )
                    self.sticky_data[channel.id] = [
                        msg.id,
                        data["message"],
                        data["delay_time"],
                    ]

                await self._send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message re-send successfully",
                    description=f"Berhasil mengirim ulang sticky message pada {instance_name} {channel.mention}",
                )
        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Resend Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(
        name="copy", description="Copy sticky message to another channel."
    )
    @app_commands.describe(source="Source channel.", target="Target channel.")
    async def copy_sticky_message(
        self,
        interaction: Interaction,
        source: discord.TextChannel | discord.Thread,
        target: discord.TextChannel | discord.Thread,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                src = await conn.fetchrow(
                    "SELECT * FROM sticky WHERE channel_id=$1;",
                    source.id,
                )
                dst = await conn.fetchrow(
                    "SELECT channel_id FROM sticky WHERE channel_id=$1;",
                    target.id,
                )

            src_target = interaction.guild.get_channel_or_thread(source.id)
            src_name = "thread" if isinstance(src_target, discord.Thread) else "channel"
            dst_target = interaction.guild.get_channel_or_thread(target.id)
            dst_name = "thread" if isinstance(dst_target, discord.Thread) else "channel"
            if not src:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada {src_name} {source.mention}",
                )
            elif dst:
                await self._send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message already exist",
                    description=f"Sticky message telah terpasang pada {dst_name} {target.mention}",
                )
            else:
                msg = await dst_target.send(
                    src["message"], allowed_mentions=self.no_mention
                )
                await self._upsert_sticky(
                    target.id, msg.id, src["message"], src["delay_time"]
                )
                self.sticky_data[target.id] = [
                    msg.id,
                    src["message"],
                    src["delay_time"],
                ]
                logger.info(
                    "STICKY MESSAGE COPIED FROM CHANNEL ID %s TO CHANNEL ID %s",
                    source.id,
                    target.id,
                )

                await self._send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message copied successfully",
                    description=(
                        f"Berhasil menyalin sticky message dari {src_name} {source.mention} "
                        f"ke {dst_name} {target.mention}\n"
                        f"**Message**: {src['message']}\n"
                        f"**Delay time**: `{src['delay_time']} secs`"
                    ),
                )
        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Copy Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(
        name="purge", description="Remove all sticky message from channels."
    )
    @app_commands.describe(
        invalid_channel_only="Only purge sticky message data from deleted channel or thread",
    )
    async def purge_sticky_message(
        self,
        interaction: Interaction,
        invalid_channel_only: bool | None,
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            # full purge needs a button tap; invalid-only touches dead channels
            proceed, confirm_msg = await self._purge_gate(
                interaction, invalid_channel_only
            )
            if not proceed:
                return
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch("SELECT * FROM sticky;")
            data = [dict(row) for row in res]
            # bounded fan-out (<=5 live calls); one bad message must not abort the run
            sem = asyncio.Semaphore(5)
            results = await asyncio.gather(
                *(
                    self._purge_one(
                        interaction.guild, sticky, sem, bool(invalid_channel_only)
                    )
                    for sticky in data
                ),
            )
            purge_ids = [
                sticky["channel_id"]
                for sticky, drop in zip(data, results, strict=True)
                if drop
            ]
            if purge_ids:
                async with self.db_pool.acquire() as conn:
                    await conn.executemany(
                        "DELETE FROM sticky WHERE channel_id=$1;",
                        [(cid,) for cid in purge_ids],
                    )
                for cid in purge_ids:
                    self.sticky_data.pop(cid, None)
            logger.info("STICKY MESSSAGES HAVE BEEN PURGED")

            await self._report_purge_result(
                interaction, confirm_msg, invalid_channel_only
            )
        else:
            await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description="Permission Manage Channel Dibutuhkan",
            )

    async def _purge_one(
        self,
        guild: discord.Guild,
        sticky: dict,
        sem: asyncio.Semaphore,
        invalid_only: bool,
    ) -> bool:
        """Delete one live sticky message; True when its DB row should be dropped."""
        cid = sticky["channel_id"]
        async with sem:
            channel = guild.get_channel_or_thread(cid)
            if channel is None:
                # not cached: deleted, an archived thread, or another guild's channel
                try:
                    channel = await self.bot.fetch_channel(cid)
                except discord.NotFound:
                    return True  # gone for good
                except (discord.Forbidden, discord.HTTPException):
                    logger.warning(
                        "Sticky purge could not resolve channel",
                        extra={"channel_id": cid},
                    )
                    return False
                if (
                    getattr(channel, "guild", None) is None
                    or channel.guild.id != guild.id
                ):
                    return False  # the sticky table is not guild-scoped; leave other guilds alone
            if invalid_only:
                return False  # channel exists, nothing to purge
            try:
                message = await channel.fetch_message(sticky["message_id"])
                await message.delete()
            except discord.NotFound:
                pass
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Sticky purge skipped a message",
                    extra={"channel_id": cid, "message_id": sticky["message_id"]},
                )
            return True

    async def _purge_gate(
        self,
        interaction: Interaction,
        invalid_channel_only: bool | None,
    ) -> tuple[bool, discord.WebhookMessage | None]:
        """Confirm gate; invalid-only touches dead channels so it skips the prompt."""
        if invalid_channel_only:
            return True, None
        return await self._confirm_purge(interaction)

    async def _report_purge_result(
        self,
        interaction: Interaction,
        confirm_msg: discord.WebhookMessage | None,
        invalid_channel_only: bool | None,
    ) -> None:
        # full purge reuses the prompt message; invalid-only never had one
        success = self._make_embed(
            interaction,
            color=discord.Color.green(),
            title="✅ All sticky message removed successfully",
            description=(
                "Berhasil menghapus sticky message pada seluruh channel dan thread"
                f"{' yang invalid' if invalid_channel_only else ''}"
            ),
        )
        if confirm_msg is None:
            await interaction.followup.send(embed=success)
            return
        try:
            await confirm_msg.edit(embed=success, view=None)
        except discord.NotFound:
            await interaction.followup.send(embed=success)

    async def _confirm_purge(
        self,
        interaction: Interaction,
    ) -> tuple[bool, discord.WebhookMessage]:
        """Button-gated confirmation; returns (proceed, prompt message)."""
        view = ConfirmView(interaction.user)
        msg = await interaction.followup.send(
            embed=self._make_embed(
                interaction,
                color=discord.Color.red(),
                title="⚠️ Confirm purge",
                description=(
                    "This will delete every live sticky message in this server and remove its sticky data. "
                    "`Use invalid_channel_only=True` instead to clean up deleted channels only."
                ),
            ),
            view=view,
            wait=True,
        )
        view.message = msg
        await view.wait()
        if view.confirmed:
            return True, msg
        # replace the prompt in place; the user never sees two embeds
        cancelled = self._make_embed(
            interaction,
            color=discord.Color.orange(),
            title="Purge cancelled",
            description=(
                "Timed out waiting for confirmation."
                if view.confirmed is None
                else "No sticky messages were deleted."
            ),
        )
        try:
            await msg.edit(embed=cancelled, view=None)
        except discord.NotFound:
            await interaction.followup.send(embed=cancelled)
        return False, msg

    @staticmethod
    def _make_embed(
        interaction: Interaction,
        color: discord.Color,
        title: str,
        description: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            color=color,
            title=title,
            description=description,
            timestamp=datetime.now(tz=UTC),
        )
        embed.set_footer(
            text=f"{interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )
        return embed

    @staticmethod
    async def _send_interaction(
        interaction: Interaction,
        color: discord.Color,
        title: str,
        description: str,
    ) -> None:
        await interaction.followup.send(
            embed=Sticky._make_embed(
                interaction, color=color, title=title, description=description
            ),
        )


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Sticky(bot))
