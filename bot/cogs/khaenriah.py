from typing import Union, Optional
from datetime import datetime

import discord
from discord.ext import commands

from bot.bot import WarnetBot
from bot.config import config
from bot.cogs.views.khaenriah import BuronanPagination


@commands.guild_only()
class Khaenriah(commands.Cog):
    BURONAN_ROLE_ID = 1022747195088318505
    KURATOR_TEYVAT_ROLE_ID = 817812012750209054
    BURONAN_MAX_LEVEL = 5

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = self.bot.get_db_pool()

    @commands.group(aliases=['buron'])
    async def buronan(self, ctx: commands.Context) -> None:
        list_of_commands = (
            f'- {ctx.prefix} buron warn <user> <reason> = Memberikan warning kepada member dan menaikkan level warn nya\n'
            f'- {ctx.prefix} buron increase/inc <user> = Menaikkan level warning secara manual\n'
            f'- {ctx.prefix} buron decrease/dec <user> = Menurunkan level warning secara manual\n'
            f'- {ctx.prefix} buron list = Melihat daftar buronan khaenriah'
        )

        if not ctx.invoked_subcommand:
            await ctx.send(f'Try:\n{list_of_commands}')

    @buronan.command(name='warn')
    async def buronan_warn(
        self,
        ctx: commands.Context,
        member: Union[discord.Member, discord.User],
        *,
        reason: Optional[str],
    ) -> None:
        if ctx.author.guild_permissions.administrator or ctx.author.get_role(
            self.KURATOR_TEYVAT_ROLE_ID
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                current_warn_level = 0
                if not data:
                    await conn.execute(
                        'INSERT INTO buronan_khaenriah (discord_id) VALUES ($1)', member.id
                    )
                else:
                    current_warn_level = data['warn_level']
                    if current_warn_level < self.BURONAN_MAX_LEVEL:
                        await conn.execute(
                            'UPDATE buronan_khaenriah SET warn_level=warn_level+1 WHERE discord_id=$1',
                            member.id,
                        )
                        current_warn_level += 1
                    else:
                        return await ctx.send(
                            content=f"**{str(member)}** has reached MAX warning level (Level {self.BURONAN_MAX_LEVEL}). Can't add more level.",
                        )

            embed = discord.Embed(
                color=discord.Color.dark_theme(),
                title='⚠️ Khaenriah Warning',
                description=f'User {member.mention} has been given a Khaenriah Warning!',
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(
                url='https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png'
            )
            embed.add_field(
                name='Current Warn Level',
                value=f'`{current_warn_level}`'
                + ('' if current_warn_level < self.BURONAN_MAX_LEVEL else ' (MAX)'),
                inline=False,
            )
            embed.add_field(
                name='Consequence', value=self._get_consequence(current_warn_level), inline=False
            )
            embed.add_field(name='Reason', value=reason, inline=False)
            embed.set_footer(
                text=f'Warned by {str(ctx.author)}', icon_url=ctx.author.display_avatar.url
            )

            warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)

            await ctx.send(embed=embed)
            await warn_log_channel.send(embed=embed)

    @buronan.command(name='increase', aliases=['inc'])
    async def buronan_increase(
        self, ctx: commands.Context, member: Union[discord.Member, discord.User]
    ) -> None:
        if ctx.author.guild_permissions.administrator or ctx.author.get_role(
            self.KURATOR_TEYVAT_ROLE_ID
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                if not data:
                    return await ctx.send(
                        content=f"**{str(member)}** never got a warning before. Can't increase warn level."
                    )

                if ctx.author == member:
                    return await ctx.send(
                        content=f"You are unable to self-increase your warn level."
                    )

                current_warn_level = data['warn_level']
                if current_warn_level < self.BURONAN_MAX_LEVEL:
                    await conn.execute(
                        'UPDATE buronan_khaenriah SET warn_level=warn_level+1 WHERE discord_id=$1',
                        member.id,
                    )
                    current_warn_level += 1
                else:
                    return await ctx.send(
                        content=f"**{str(member)}** has reached MAX warning level (Level {self.BURONAN_MAX_LEVEL}). Can't add more level.",
                    )

            warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
            desc = f"**{str(member)}** warn level has been increased manually from `{data['warn_level']}` to `{current_warn_level}`"
            embed = discord.Embed(
                title='KHAENRIAH WARN LEVEL IS INCREASED',
                description=desc,
                timestamp=datetime.now(),
                color=discord.Color.dark_theme(),
            )
            embed.set_thumbnail(
                url='https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png'
            )
            embed.set_footer(
                text=f'Executed by {str(ctx.author)}', icon_url=ctx.author.display_avatar.url
            )

            await ctx.send(embed=embed)
            await warn_log_channel.send(embed=embed)

    @buronan.command(name='decrease', aliases=['dec'])
    async def buronan_decrease(
        self, ctx: commands.Context, member: Union[discord.Member, discord.User]
    ) -> None:
        if ctx.author.guild_permissions.administrator or ctx.author.get_role(
            self.KURATOR_TEYVAT_ROLE_ID
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                if not data:
                    return await ctx.send(
                        content=f"**{str(member)}** never got a warning before. Can't decrease warn level."
                    )

                if ctx.author == member:
                    return await ctx.send(
                        content=f"You are unable to self-decrease your warn level."
                    )

                current_warn_level = data['warn_level']
                if current_warn_level > 0:
                    await conn.execute(
                        'UPDATE buronan_khaenriah SET warn_level=warn_level-1 WHERE discord_id=$1',
                        member.id,
                    )
                    current_warn_level -= 1
                else:
                    await conn.execute(
                        'DELETE FROM buronan_khaenriah WHERE discord_id=$1', member.id
                    )
                    return await ctx.send(
                        content=f"**{str(member)}** has been removed from database.",
                    )

            warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
            desc = f"**{str(member)}** warn level has been decreased manually from `{data['warn_level']}` to `{current_warn_level}`"
            embed = discord.Embed(
                title='KHAENRIAH WARN LEVEL IS DECREASED',
                description=desc,
                timestamp=datetime.now(),
                color=discord.Color.dark_theme(),
            )
            embed.set_thumbnail(
                url='https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png'
            )
            embed.set_footer(
                text=f'Executed by {str(ctx.author)}', icon_url=ctx.author.display_avatar.url
            )

            await ctx.send(embed=embed)
            await warn_log_channel.send(embed=embed)

    @buronan.command(name='list')
    async def buronan_list(self, ctx: commands.Context) -> None:
        await ctx.typing()
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM buronan_khaenriah ORDER BY warn_level DESC;")
            all_records = [dict(row) for row in records]

        view = BuronanPagination(buronan_list_data=all_records)
        await view.start(ctx)

    def _get_consequence(self, warn_level: int) -> str:
        buronan_role_mention = f'<@&{self.BURONAN_ROLE_ID}>'
        consequences = [
            'No consequence',
            'Subtract exp for a certain amount',
            f'Receive {buronan_role_mention} for `3 Days`',
            f'Receive {buronan_role_mention} for `7 Days`',
            f'Receive {buronan_role_mention} for `30 Days`',
            f'Receive {buronan_role_mention} permanently',
        ]

        return consequences[warn_level]


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Khaenriah(bot))
