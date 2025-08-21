import logging
from datetime import UTC, datetime

import discord
from discord.ext import commands

from bot import config
from bot.bot import WarnetBot
from bot.cogs.views.khaenriah import BuronanPagination
from bot.helper import ctx_guard

logger = logging.getLogger(__name__)


@commands.guild_only()
class Khaenriah(commands.Cog):
    BURONAN_ROLE_ID = 1022747195088318505
    KURATOR_TEYVAT_ROLE_ID = 817812012750209054
    BURONAN_MAX_LEVEL = 5

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

    @commands.group(aliases=["buron"])
    async def buronan(self, ctx: commands.Context) -> None:
        list_of_commands = (
            f"- {ctx.prefix}buron warn <user> <reason> = Memberikan warning kepada member dan menaikkan level warn nya\n"
            f"- {ctx.prefix}buron increase/inc <user> = Menaikkan level warning secara manual\n"
            f"- {ctx.prefix}buron decrease/dec <user> = Menurunkan level warning secara manual\n"
            f"- {ctx.prefix}buron list = Melihat daftar buronan khaenriah"
        )

        if not ctx.invoked_subcommand:
            await ctx.send(f"Try:\n{list_of_commands}")

    @buronan.command(name="warn")
    @ctx_guard(role_id=KURATOR_TEYVAT_ROLE_ID)
    async def buronan_warn(
        self,
        ctx: commands.Context,
        member: discord.Member | discord.User,
        *,
        reason: str | None,
    ) -> None:
        if not ctx.guild:
            return

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT * FROM buronan_khaenriah WHERE discord_id=$1", member.id
            )

            current_warn_level = 0
            if not data:
                await conn.execute(
                    "INSERT INTO buronan_khaenriah (discord_id) VALUES ($1)",
                    member.id,
                )
            else:
                current_warn_level = data["warn_level"]
                if current_warn_level < self.BURONAN_MAX_LEVEL:
                    await conn.execute(
                        "UPDATE buronan_khaenriah SET warn_level=warn_level+1 WHERE discord_id=$1",
                        member.id,
                    )
                    current_warn_level += 1
                else:
                    await ctx.send(
                        content=f"**{member.name}** has reached MAX warning level (Level {self.BURONAN_MAX_LEVEL}). Can't add more level.",
                    )
                    return

        embed = discord.Embed(
            color=discord.Color.dark_theme(),
            title="⚠️ Khaenriah Warning",
            description=f"User {member.mention} has been given a Khaenriah Warning!",
            timestamp=datetime.now(tz=UTC),
        )
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png"
        )
        embed.add_field(
            name="Current Warn Level",
            value=f"`{current_warn_level}`"
            + ("" if current_warn_level < self.BURONAN_MAX_LEVEL else " (MAX)"),
            inline=False,
        )
        embed.add_field(
            name="Consequence",
            value=self._get_consequence(current_warn_level),
            inline=False,
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(
            text=f"Warned by {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
        if warn_log_channel is None:
            logger.error(
                "Channel not found",
                extra={"channel_id": config.WARN_LOG_CHANNEL_ID},
            )
            return

        await ctx.send(embed=embed)
        await warn_log_channel.send(embed=embed)
        return

    @buronan.command(name="increase", aliases=["inc"])
    @ctx_guard(role_id=KURATOR_TEYVAT_ROLE_ID)
    async def buronan_increase(
        self, ctx: commands.Context, member: discord.Member | discord.User
    ) -> None:
        if not ctx.guild:
            return

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT * FROM buronan_khaenriah WHERE discord_id=$1", member.id
            )

            if not data:
                await ctx.send(
                    content=f"**{member.name}** never got a warning before. Can't increase warn level."
                )
                return

            if ctx.author == member:
                await ctx.send(
                    content="You are unable to self-increase your warn level."
                )
                return

            current_warn_level = data["warn_level"]
            if current_warn_level < self.BURONAN_MAX_LEVEL:
                await conn.execute(
                    "UPDATE buronan_khaenriah SET warn_level=warn_level+1 WHERE discord_id=$1",
                    member.id,
                )
                current_warn_level += 1
            else:
                await ctx.send(
                    content=f"**{member.name}** has reached MAX warning level (Level {self.BURONAN_MAX_LEVEL}). Can't add more level.",
                )
                return

        warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
        if warn_log_channel is None:
            logger.error(
                "Channel not found",
                extra={"channel_id": config.WARN_LOG_CHANNEL_ID},
            )
            return

        desc = f"**{member.name}** warn level has been increased manually from `{data['warn_level']}` to `{current_warn_level}`"
        embed = discord.Embed(
            title="KHAENRIAH WARN LEVEL IS INCREASED",
            description=desc,
            timestamp=datetime.now(tz=UTC),
            color=discord.Color.dark_theme(),
        )
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png"
        )
        embed.set_footer(
            text=f"Executed by {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        await warn_log_channel.send(embed=embed)
        await ctx.send(embed=embed)
        return

    @buronan.command(name="decrease", aliases=["dec"])
    @ctx_guard(role_id=KURATOR_TEYVAT_ROLE_ID)
    async def buronan_decrease(
        self, ctx: commands.Context, member: discord.Member | discord.User
    ) -> None:
        if not ctx.guild:
            return

        async with self.db_pool.acquire() as conn:
            data = await conn.fetchrow(
                "SELECT * FROM buronan_khaenriah WHERE discord_id=$1", member.id
            )

            if not data:
                await ctx.send(
                    content=f"**{member.name}** never got a warning before. Can't decrease warn level."
                )
                return

            if ctx.author == member:
                await ctx.send(
                    content="You are unable to self-decrease your warn level."
                )
                return

            current_warn_level = data["warn_level"]
            if current_warn_level > 0:
                await conn.execute(
                    "UPDATE buronan_khaenriah SET warn_level=warn_level-1 WHERE discord_id=$1",
                    member.id,
                )
                current_warn_level -= 1
            else:
                await conn.execute(
                    "DELETE FROM buronan_khaenriah WHERE discord_id=$1", member.id
                )
                await ctx.send(
                    content=f"**{member.name}** has been removed from database.",
                )
                return

        warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
        warn_log_channel = ctx.guild.get_channel(config.WARN_LOG_CHANNEL_ID)
        if warn_log_channel is None:
            logger.error(
                "Channel not found",
                extra={"channel_id": config.WARN_LOG_CHANNEL_ID},
            )
            return

        desc = f"**{member.name}** warn level has been decreased manually from `{data['warn_level']}` to `{current_warn_level}`"
        embed = discord.Embed(
            title="KHAENRIAH WARN LEVEL IS DECREASED",
            description=desc,
            timestamp=datetime.now(tz=UTC),
            color=discord.Color.dark_theme(),
        )
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png"
        )
        embed.set_footer(
            text=f"Executed by {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        await warn_log_channel.send(embed=embed)
        await ctx.send(embed=embed)
        return

    @buronan.command(name="list")
    async def buronan_list(self, ctx: commands.Context) -> None:
        await ctx.typing()
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT * FROM buronan_khaenriah ORDER BY warn_level DESC;"
            )
            all_records = [dict(row) for row in records]

        view = BuronanPagination(buronan_list_data=all_records)
        await view.start(ctx)

    def _get_consequence(self, warn_level: int) -> str:
        buronan_role_mention = f"<@&{self.BURONAN_ROLE_ID}>"
        consequences = [
            "No consequence",
            "Subtract exp for a certain amount",
            f"Receive {buronan_role_mention} for `3 Days`",
            f"Receive {buronan_role_mention} for `7 Days`",
            f"Receive {buronan_role_mention} for `30 Days`",
            f"Receive {buronan_role_mention} permanently",
        ]

        return consequences[warn_level]


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Khaenriah(bot))
