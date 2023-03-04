from typing import Union
from datetime import datetime

import discord
from discord.ext import commands

from bot.bot import WarnetBot
from bot.config import config


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
            f'- {ctx.prefix} buron warn <user> = Memberikan warning kepada member dan menaikkan level warn nya\n'
            f'- {ctx.prefix} buron increase/inc <user> = Menaikkan level warning secara manual\n'
            f'- {ctx.prefix} buron decrease/dec <user> = Menurunkan level warning secara manual\n'
            f'- {ctx.prefix} buron list = Melihat daftar buronan khaenriah'
        )

        if ctx.invoked_subcommand is None:
            await ctx.send(f'Try:\n{list_of_commands}')

    @buronan.command(name='warn')
    async def buronan_warn(
        self, ctx: commands.Context, member: Union[discord.Member, discord.User]
    ) -> None:
        if (
            ctx.author.guild_permissions.administrator
            or ctx.author.get_role(self.KURATOR_TEYVAT_ROLE_ID) is not None
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                current_warn_level = 0
                if data is None:
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
        if (
            ctx.author.guild_permissions.administrator
            or ctx.author.get_role(self.KURATOR_TEYVAT_ROLE_ID) is not None
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                if data is None:
                    return await ctx.send(
                        content=f"**{str(member)}** never got a warning before. Can't increase warn level."
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

            await ctx.send(
                content=f"**{str(member)}** warn level has been increased manually from `{data['warn_level']}` to `{current_warn_level}`"
            )

    @buronan.command(name='decrease', aliases=['dec'])
    async def buronan_decrease(
        self, ctx: commands.Context, member: Union[discord.Member, discord.User]
    ) -> None:
        if (
            ctx.author.guild_permissions.administrator
            or ctx.author.get_role(self.KURATOR_TEYVAT_ROLE_ID) is not None
        ):
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow(
                    'SELECT * FROM buronan_khaenriah WHERE discord_id=$1', member.id
                )

                if data is None:
                    return await ctx.send(
                        content=f"**{str(member)}** never got a warning before. Can't decrease warn level."
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

            await ctx.send(
                content=f"**{str(member)}** warn level has been decreased manually from `{data['warn_level']}` to `{current_warn_level}`"
            )

    @buronan.command(name='list')
    async def buronan_list(self, ctx: commands.Context) -> None:
        pass

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
