import asyncio
import logging
from datetime import UTC, datetime

import discord
from discord import AllowedMentions, Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.views.sticky import StickyPagination
from bot.helper import app_guard

logger = logging.getLogger(__name__)


@commands.guild_only()
class Sticky(commands.GroupCog, group_name="sticky"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.sticky_data: dict[int, list] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._bg_tasks: set[asyncio.Task] = set()
        self.no_mention = AllowedMentions(
            everyone=False,
            users=False,
            roles=False,
            replied_user=False,
        )

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM sticky ORDER BY channel_id ASC;")
            data_list = [dict(row) for row in records]
            for data in data_list:
                self.sticky_data[data["channel_id"]] = [
                    data["message_id"],
                    data["message"],
                    data["delay_time"],
                ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return
        res = self.sticky_data.get(message.channel.id)
        if not res:
            return
        task = asyncio.create_task(self._repost_sticky(message.channel, res[0], res[1], res[2]))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _fetch_previous_sticky(
        self, channel: discord.abc.Messageable, sticky_id: int
    ) -> discord.Message | None:
        try:
            return await channel.fetch_message(sticky_id)  # type: ignore[attr-defined]
        except discord.NotFound:
            current = self.sticky_data.get(channel.id)  # type: ignore[attr-defined]
            if current is not None and current[0] != sticky_id:
                return None
            self.sticky_data.pop(channel.id, None)
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM sticky WHERE channel_id = $1", channel.id
                )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Sticky fetch failed", extra={"channel_id": getattr(channel, "id", "?")}
            )
        return None

    async def _repost_sticky(
        self, channel: discord.abc.Messageable, sticky_id: int, sticky_msg: str, delay: int,
    ) -> None:
        # per-channel lock, offload so on_message never blocks
        lock = self._locks.setdefault(channel.id, asyncio.Lock())  # type: ignore[attr-defined]
        async with lock:
            try:
                # --- race guard: refresh to current data inside lock ---
                # on_message captures sticky_id at task creation time; if multiple
                # messages arrive quickly, the first task updates sticky_data/DB
                # while the second task still holds the old id. Without a check
                # the stale task fetches the old (now deleted) id -> NotFound ->
                # it incorrectly DELETEs the live DB row (data loss).
                current = self.sticky_data.get(channel.id)  # type: ignore[attr-defined]
                if current is None:
                    return
                # If this task is stale (id changed under us), there is already a
                # newer sticky at the bottom that covers all messages sent while
                # the first task was sleeping. No need to repost again.
                if current[0] != sticky_id:
                    return
                # Always use the latest message/delay from cache (edits may have
                # changed them after this task was queued).
                sticky_id, sticky_msg, delay = current  # type: ignore[misc]

                prev = await self._fetch_previous_sticky(channel, sticky_id)
                if prev is None:
                    return

                await asyncio.sleep(delay)

                # Re-validate cache after sleep -- an edit could have changed
                # message/delay while we were sleeping.
                cur3 = self.sticky_data.get(channel.id)  # type: ignore[attr-defined]
                if cur3 is not None:
                    if cur3[0] != sticky_id:
                        return
                    sticky_msg = cur3[1]

                # Send new sticky BEFORE deleting old one so a send failure
                # does not leave the channel with no sticky and a dangling DB row.
                try:
                    msg = await channel.send(sticky_msg, allowed_mentions=self.no_mention)  # type: ignore[attr-defined]
                except (discord.Forbidden, discord.HTTPException):
                    logger.warning("Sticky send failed", extra={"channel_id": getattr(channel, 'id', '?')})
                    return

                try:
                    await prev.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    logger.warning("Sticky delete failed", extra={"channel_id": getattr(channel, 'id', '?')})

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE sticky SET message_id=$2 WHERE channel_id=$1;",
                        channel.id,
                        msg.id,
                    )
                self.sticky_data[channel.id] = [msg.id, sticky_msg, delay]

            except Exception:
                logger.exception("Unexpected sticky repost error", extra={"channel_id": getattr(channel, 'id', '?')})

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
    @app_guard(
        manage_channel=True,
    )
    async def add_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 0, 2000],
        channel: discord.TextChannel | discord.Thread,
        delay_time: app_commands.Range[int, 2, 1800] | None,
    ) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return None

        async with self.db_pool.acquire() as conn:
            res = await conn.fetchrow(
                "SELECT channel_id FROM sticky WHERE channel_id=$1;", channel.id
            )

        target = interaction.guild.get_channel_or_thread(channel.id)
        if target is None:
            logger.error("Channel not found", extra={"channel_id": channel.id})
            return None

        instance_name = "thread" if isinstance(target, discord.Thread) else "channel"
        if res:
            return await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ Sticky message already exist",
                description=f"Sticky message telah terpasang pada {instance_name} {channel.mention}",
            )

        message = "\n".join(message.split("\\n"))
        msg = await target.send(message)
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
            extra={
                "channel_id": channel.id,
                "msgs": message,
                "delay_time": delay_time,
            },
        )

        return await self._send_interaction(
            interaction,
            color=discord.Color.green(),
            title="✅ Sticky message successfully given",
            description=(
                f"Berhasil menambahkan sticky message pada {instance_name} {channel.mention}\n"
                f"**Message**: {message}\n"
                f"**Delay time**: `{delay_time} secs`"
            ),
        )

    @app_commands.command(name="edit", description="Edit sticky message.")
    @app_commands.describe(
        message="New sticky message.",
        channel="Channel name.",
        delay_time="New delay time after new message is sent on a channel (in seconds).",
    )
    @app_guard(
        manage_channel=True,
    )
    async def edit_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 0, 2000],
        channel: discord.TextChannel | discord.Thread,
        delay_time: app_commands.Range[int, 2, 1800] | None,
    ) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return None

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT channel_id,message_id,delay_time FROM sticky WHERE channel_id=$1;",
                channel.id,
            )

        target = interaction.guild.get_channel_or_thread(channel.id)
        if target is None:
            logger.error("Channel not found", extra={"channel_id": channel.id})
            return None

        instance_name = "thread" if isinstance(target, discord.Thread) else "channel"
        if not data:
            return await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ Sticky message not exist",
                description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
            )

        if not delay_time:
            delay_time = data["delay_time"]

        try:
            sticky_msg = await channel.fetch_message(data["message_id"])
            message = "\n".join(message.split("\\n"))
            sticky_data = await sticky_msg.edit(content=message)
        except discord.errors.NotFound:
            message = "\n".join(message.split("\\n"))
            sticky_data = await target.send(message)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sticky SET message=$2, delay_time=$3 WHERE channel_id=$1;",
                channel.id,
                message,
                delay_time,
            )

        self.sticky_data[channel.id] = [sticky_data.id, message, delay_time]

        return await self._send_interaction(
            interaction,
            color=discord.Color.green(),
            title="✅ Sticky message update successfully",
            description=(
                f"Berhasil memperbarui sticky message pada {instance_name} {channel.mention}\n"
                f"**New message**: {message}\n"
                f"**Delay time**: `{delay_time} secs`"
            ),
        )

    @app_commands.command(
        name="remove", description="Remove sticky message from channel."
    )
    @app_commands.describe(channel="Target channel.")
    @app_guard(
        manage_channel=True,
    )
    async def remove_sticky_message(
        self,
        interaction: Interaction,
        channel: discord.TextChannel | discord.Thread,
    ) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            return None

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT channel_id,message_id FROM sticky WHERE channel_id=$1;",
                channel.id,
            )

        target = interaction.guild.get_channel_or_thread(channel.id)
        if target is None:
            logger.error("Channel not found", extra={"channel_id": channel.id})
            return None

        instance_name = "thread" if isinstance(target, discord.Thread) else "channel"
        if not data:
            return await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ Sticky message not exist",
                description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
            )

        try:
            sticky = await channel.fetch_message(data["message_id"])
            await sticky.delete()
        except discord.errors.NotFound:
            pass

        async with self.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM sticky WHERE channel_id=$1;", channel.id)

        self.sticky_data.pop(channel.id)
        logger.info(
            "NEW STICKY MESSSAGE HAS BEEN REMOVED", extra={"channel_id": channel.id}
        )
        return await self._send_interaction(
            interaction,
            color=discord.Color.green(),
            title="✅ Sticky message removed successfully",
            description=f"Berhasil menghapus sticky message pada {instance_name} {channel.mention}",
        )

    @app_commands.command(
        name="resend", description="Resend sticky message to channels."
    )
    @app_commands.describe(channel="Target Channel")
    @app_guard(
        manage_channel=True,
    )
    async def resend_sticky_message(
        self,
        interaction: Interaction,
        channel: discord.TextChannel | discord.Thread,
    ) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            return None

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT * FROM sticky WHERE channel_id=$1;",
                channel.id,
            )

        target = interaction.guild.get_channel_or_thread(channel.id)
        if target is None:
            logger.error("Channel not found", extra={"channel_id": channel.id})
            return None

        instance_name = "thread" if isinstance(target, discord.Thread) else "channel"
        if not data:
            return await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ Sticky message not exist",
                description=f"Tidak ada sticky message pada {instance_name} {channel.mention}",
            )

        try:
            await channel.fetch_message(data["message_id"])
            return await self._send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ Sticky message already exist",
                description=f"Sticky message telah terpasang pada {instance_name} {channel.mention}",
            )
        except discord.errors.NotFound:
            msg = await target.send(data["message"])

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE sticky SET message_id=$2 WHERE channel_id=$1;",
                    channel.id,
                    msg.id,
                )

            self.sticky_data[channel.id] = [
                msg.id,
                data["message"],
                data["delay_time"],
            ]

            return await self._send_interaction(
                interaction,
                color=discord.Color.green(),
                title="✅ Sticky message re-send successfully",
                description=f"Berhasil mengirim ulang sticky message pada {instance_name} {channel.mention}",
            )

    @app_commands.command(
        name="purge", description="Remove all sticky message from channels."
    )
    @app_commands.describe(
        invalid_channel_only="Only purge sticky message data from deleted channel or thread"
    )
    @app_guard(
        manage_channel=True,
    )
    async def purge_sticky_message(
        self,
        interaction: Interaction,
        invalid_channel_only: bool,
    ) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            return None

        async with self.db_pool.acquire() as conn:
            res = await conn.fetch("SELECT * FROM sticky;")
            data = [dict(row) for row in res]
            invalid_channel_id_list = []
            for sticky in data:
                try:
                    channel = interaction.guild.get_channel_or_thread(
                        sticky["channel_id"]
                    )
                    if channel is None:
                        logger.error(
                            "Channel not found",
                            extra={"channel_id": sticky["channel_id"]},
                        )
                        return None
                    message = await channel.fetch_message(sticky["message_id"])
                    if not invalid_channel_only:
                        await message.delete()
                except AttributeError:  # This is happened if channel is None
                    invalid_channel_id_list.append([sticky["channel_id"]])
                except discord.errors.NotFound:
                    continue

            if not invalid_channel_only:
                await conn.execute("TRUNCATE TABLE sticky;")
            else:
                await conn.executemany(
                    "DELETE FROM sticky WHERE channel_id=$1;",
                    invalid_channel_id_list,
                )

        logger.info("STICKY MESSSAGES HAVE BEEN PURGED")
        return await self._send_interaction(
            interaction,
            color=discord.Color.green(),
            title="✅ All sticky message removed successfully",
            description=(
                "Berhasil menghapus sticky message pada seluruh channel dan thread"
                f"{' yang invalid' if invalid_channel_only else ''}"
            ),
        )

    @staticmethod
    async def _send_interaction(
        interaction: Interaction, color: discord.Color, title: str, description: str
    ) -> None:
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
        await interaction.followup.send(embed=embed)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Sticky(bot))
