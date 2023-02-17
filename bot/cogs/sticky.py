import discord
from discord import Interaction, app_commands
from discord.ext import commands

from bot.bot import WarnetBot
from bot.cogs.views.sticky import StickyPagination

from datetime import datetime
from typing import Union

class Sticky(commands.GroupCog, group_name="sticky"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message)->None:
        async with self.db_pool.acquire() as conn:
            res = await conn.fetch(
                "SELECT channel_id,message_id,message FROM sticky WHERE channel_id = $1", message.channel.id
            )
            if not message.author.bot and res:
                data = dict(res[0])
                if message.channel.id == data['channel_id']:
                    sticky = await message.channel.fetch_message(data['message_id'])
                    await sticky.delete()
                    msg = await message.channel.send(data['message'])
                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE sticky SET message_id = $2 WHERE channel_id = $1;", message.channel.id, msg.id
                        )
    
    @commands.guild_only()
    @app_commands.command(name="list-sticky", description="List channel with sticky message")
    async def list_sticky_messages(
        self,
        interaction: Interaction
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT * FROM sticky ORDER BY channel_id ASC;"
                )
                record = [dict(row) for row in res]
                
                view = StickyPagination(list_data=record)
                await view.start(interaction)
        else:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To View List Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
                timestamp=datetime.now()
            )

            embed.set_footer(
                text=f"{str(interaction.user)}",
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=embed)

    @commands.guild_only()
    @app_commands.command(name="add-sticky", description="Add sticky message to channel")
    @app_commands.describe(message="Sticky Message", channel="Target Channel")
    async def add_sticky_message(
        self,
        interaction: Interaction,
        message: app_commands.Range[str, 0],
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread]
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id FROM sticky WHERE channel_id = $1", channel.id
                )
            if not res:
                target = self.bot.get_channel(channel.id)
                id = await target.send(message)
            
                async with self.db_pool.acquire() as conn:
                    await conn.executemany(
                        "INSERT INTO sticky (channel_id,message_id,message) VALUES ($1,$2,$3);",
                        [(channel.id, id.id, message)]
                 )

                embed = discord.Embed(
                    color=discord.Color.green(),
                    title="✅ Sticky message successfully given",
                    description=f"Berhasil menambahkan sticky message pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
            else:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    title="❌ Sticky message already exist",
                    description=f"Sticky message telah terpasang pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
        else:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Create Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
                timestamp=datetime.now()
            )

        embed.set_footer(
            text=f"{str(interaction.user)}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.followup.send(embed=embed)
    
    @commands.guild_only()
    @app_commands.command(name="edit-sticky", description="Edit sticky message")
    @app_commands.describe(message="New sticky message", channel="Channel Name")
    async def edit_sticky_message(
        self, 
        interaction: Interaction,
        message: app_commands.Range[str, 0],
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread]
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id,message_id FROM sticky WHERE channel_id = $1", channel.id
                )
            if not res:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
            else:
                data = dict(res[0])

                sticky = await channel.fetch_message(data['message_id'])
                await sticky.edit(content=message)

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE sticky SET message = $2 WHERE channel_id = $1;", channel.id, message
                    )

                embed = discord.Embed(
                    color=discord.Color.green(),
                    title="✅ Sticky message update successfully",
                    description=f"Berhasil memperbaharui sticky message pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
        else:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
                timestamp=datetime.now()
            )

        embed.set_footer(
            text=f"{str(interaction.user)}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.followup.send(embed=embed)
        

    @commands.guild_only()
    @app_commands.command(name="remove-sticky", description="Remove sticky message from channel")
    @app_commands.describe(channel="Target Channel")
    async def remove_sticky_message(
        self,
        interaction: Interaction,
        channel: Union[discord.TextChannel, discord.ForumChannel, discord.Thread]
    ) -> None:
        await interaction.response.defer()
        if interaction.permissions.manage_channels:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetch(
                    "SELECT channel_id,message_id FROM sticky WHERE channel_id = $1", channel.id
                )
            if not res:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    title="❌ Sticky message not exist",
                    description=f"Tidak ada sticky message pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
            else:
                data = dict(res[0])

                sticky = await channel.fetch_message(data['message_id'])
                await sticky.delete()

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM sticky WHERE channel_id = $1;", channel.id
                    )

                embed = discord.Embed(
                    color=discord.Color.green(),
                    title="✅ Sticky message removed successfully",
                    description=f"Berhasil menghapus sticky message pada channel <#{channel.id}>",
                    timestamp=datetime.now()
                )
        else:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="❌ You Don't Have Permission To Delete Sticky Message",
                description=f"Permission Manage Channel Dibutuhkan",
                timestamp=datetime.now()
            )

        embed.set_footer(
            text=f"{str(interaction.user)}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.followup.send(embed=embed)

async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Sticky(bot))
