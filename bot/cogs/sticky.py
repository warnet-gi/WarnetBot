import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.views.sticky import StickyPagination

import asyncio
from datetime import datetime
from typing import Union, List, Dict, Any


@commands.guild_only()
class Sticky(commands.GroupCog, group_name="sticky"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.sticky_data: Dict[int, List[int, str]] = dict()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM sticky ORDER BY channel_id ASC;")
            data_list = [dict(row) for row in records]
            for data in data_list:
                self.sticky_data[data['channel_id']] = [data['message_id'], data['message']]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        res = None
        if message.channel.id in self.sticky_data:
            res = self.sticky_data[message.channel.id]
            sticky_message_id = res[0]
            sticky_message = res[1]

        if res and message.author != self.bot.user:
            try:
                sticky = await message.channel.fetch_message(sticky_message_id)
            except discord.errors.NotFound:
                return

            await sticky.delete()
            await asyncio.sleep(2)
            msg = await message.channel.send(sticky_message)

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE sticky SET message_id = $2 WHERE channel_id = $1;",
                    message.channel.id,
                    msg.id,
                )

            self.sticky_data[message.channel.id] = [msg.id, sticky_message]

    @app_commands.command(name="list", description="List channel with sticky message.")
    async def list_sticky_messages(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        async with self.db_pool.acquire() as conn:
            res = await conn.fetch("SELECT * FROM sticky ORDER BY channel_id ASC;")
            record = [dict(row) for row in res]

            view = StickyPagination(list_data=record)
            await view.start(interaction)

    @app_commands.command(name="add", description="Add sticky message to a channel.")
    @app_commands.describe(message="Sticky message.", channel="Target channel.")
    async def add_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 0, 2000],
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread],
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id FROM sticky WHERE channel_id = $1;", channel.id
                )
            if not res:
                target = self.bot.get_channel(channel.id)
                message = '\n'.join(message.split('\\n'))
                msg = await target.send(message)

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO sticky (channel_id,message_id,message) VALUES ($1,$2,$3);",
                        channel.id,
                        msg.id,
                        message,
                    )

                self.sticky_data[channel.id] = [msg.id, message]

                await send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message successfully given",
                    description=f"Berhasil menambahkan sticky message pada channel {channel.mention}",
                )

            else:
                await send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message already exist",
                    description=f"Sticky message telah terpasang pada channel {channel.mention}",
                )

        else:
            await send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Create Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(name="edit", description="Edit sticky message.")
    @app_commands.describe(message="New sticky message.", channel="Channel name.")
    async def edit_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 0, 2000],
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread],
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id,message_id FROM sticky WHERE channel_id = $1;",
                    channel.id,
                )
            if not res:
                await send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada channel {channel.mention}",
                )
            else:
                data = dict(res[0])

                try:
                    sticky_msg = await channel.fetch_message(data["message_id"])
                    message = '\n'.join(message.split('\\n'))
                    sticky_data = await sticky_msg.edit(content=message)
                except discord.errors.NotFound:
                    sticky_channel = self.bot.get_channel(channel.id)
                    message = '\n'.join(message.split('\\n'))
                    sticky_data = await sticky_channel.send(message)

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE sticky SET message = $2 WHERE channel_id = $1;",
                        channel.id,
                        message,
                    )

                self.sticky_data[channel.id] = [sticky_data.id, message]

                await send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message update successfully",
                    description=f"Berhasil memperbaharui sticky message pada channel {channel.mention}",
                )
        else:
            await send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(name="remove", description="Remove sticky message from channel.")
    @app_commands.describe(channel="Target channel.")
    async def remove_sticky_message(
        self,
        interaction: Interaction,
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread],
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id,message_id FROM sticky WHERE channel_id = $1;",
                    channel.id,
                )

            if not res:
                await send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada channel {channel.mention}",
                )
            else:
                data = dict(res[0])
                try:
                    sticky = await channel.fetch_message(data["message_id"])
                    await sticky.delete()
                except discord.errors.NotFound:
                    pass

                async with self.db_pool.acquire() as conn:
                    await conn.execute("DELETE FROM sticky WHERE channel_id = $1;", channel.id)

                self.sticky_data.pop(channel.id)

                await send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message removed successfully",
                    description=f"Berhasil menghapus sticky message pada channel {channel.mention}",
                )
        else:
            await send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
            )

    @app_commands.command(name="re-send", description="Re-send sticky message to channels.")
    @app_commands.describe(channel="Target Channel")
    async def fix_sticky_message(
        self,
        interaction: Interaction,
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread],
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT * FROM sticky WHERE channel_id = $1;",
                    channel.id,
                )

            if not res:
                await send_interaction(
                    interaction,
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada channel {channel.mention}",
                )
            else:
                data = dict(res[0])
                try:
                    await channel.fetch_message(data["message_id"])
                    return await send_interaction(
                        interaction,
                        color=discord.Color.red(),
                        title="❌ Sticky message already exist",
                        description=f"Sticky message telah terpasang pada channel {channel.mention}",
                    )
                except discord.errors.NotFound:
                    target = self.bot.get_channel(channel.id)
                    msg = await target.send(data["message"])

                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE sticky SET message_id = $2 WHERE channel_id = $1;",
                            channel.id,
                            msg.id,
                        )

                    self.sticky_data[channel.id] = [msg.id, data["message"]]

                await send_interaction(
                    interaction,
                    color=discord.Color.green(),
                    title="✅ Sticky message re-send successfully",
                    description=f"Berhasil mengirim ulang sticky message pada channel {channel.mention}",
                )

    @app_commands.command(name="purge", description="Remove all sticky message from channels.")
    async def purge_sticky_message(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch("SELECT * FROM sticky;")
                data = [dict(row) for row in res]
                for sticky in data:
                    try:
                        channel = await self.bot.fetch_channel(sticky["channel_id"])
                        message = await channel.fetch_message(sticky["message_id"])
                        await message.delete()
                    except discord.errors.NotFound:
                        continue

                await conn.execute("TRUNCATE TABLE sticky;")

            await send_interaction(
                interaction,
                color=discord.Color.green(),
                title="✅ All sticky message removed successfully",
                description=f"Berhasil menghapus seluruh sticky message pada channel",
            )

        else:
            await send_interaction(
                interaction,
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
            )


async def send_interaction(
    interaction: Interaction, color: discord.Color, title: str, description: str
) -> None:
    embed = discord.Embed(
        color=color,
        title=title,
        description=description,
        timestamp=datetime.now(),
    )
    embed.set_footer(
        text=f"{str(interaction.user)}",
        icon_url=interaction.user.display_avatar.url,
    )
    await interaction.followup.send(embed=embed)


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Sticky(bot))
