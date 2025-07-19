import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.temprole.time import parse_time_string
from bot.config import BLACKLIST_GA_ROLE_ID, GUILD_ID

logger = logging.getLogger(__name__)


@commands.guild_only()
class Temporary(commands.GroupCog, group_name="warnet-temp"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not self._check_temprole.is_running():
            self._check_temprole.start()

    @app_commands.command(name="add", description="Adds a temprole to user")
    @app_commands.describe(
        user="User to add temprole to",
        duration="Example: 1d2h3m4s",
        role="Role to add",
    )
    async def add_temporary_role(
        self,
        interaction: Interaction,
        user: discord.Member,
        duration: str,
        role: discord.Role,
    ) -> None:
        await interaction.response.defer()
        if role.id == BLACKLIST_GA_ROLE_ID:
            return await interaction.followup.send(
                "Cannot add blacklist giveaway role!!", ephemeral=True
            )

        if interaction.guild and not interaction.user.guild_permissions.manage_roles:
            return await interaction.followup.send(
                "You do not have permission to manage roles", ephemeral=True
            )

        try:
            duration_seconds = parse_time_string(duration)
            if duration_seconds < 60 * 1:
                return await interaction.followup.send(
                    "Duration must be at least 1 minute", ephemeral=True
                )
            if duration_seconds > 60 * 60 * 24 * 365:
                return await interaction.followup.send(
                    "Duration must be at most 1 year", ephemeral=True
                )
            await user.add_roles(role)
        except ValueError:
            return await interaction.followup.send(
                "Invalid duration format", ephemeral=True
            )
        except discord.HTTPException:
            return await interaction.followup.send(
                "Something went wrong", ephemeral=True
            )

        logger.info(
            "Added temporary role",
            extra={
                "user": user.id,
                "role": role.id,
                "duration_seconds": duration_seconds,
            },
        )
        total_duration = datetime.now(UTC) + timedelta(seconds=duration_seconds)

        async with self.db_pool.acquire() as conn:
            query = """
                INSERT INTO temp_role (user_id, role_id, end_time)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, role_id)
                DO UPDATE SET end_time = EXCLUDED.end_time
            """
            await conn.execute(query, user.id, role.id, total_duration)

        embed = discord.Embed(
            title="Role Added",
            description=f"Successfully added the role {role.mention} to the {user.mention}\nremove <t:{int(total_duration.timestamp())}:R>",
            color=discord.Color.green(),
        )
        return await interaction.followup.send(embed=embed)

    @tasks.loop(seconds=60)
    async def _check_temprole(self) -> None:
        current_time = datetime.now(UTC)
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning("Guild not found, skipping temporary role check")
            return
        id_success = []

        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT id, user_id, role_id FROM temp_role WHERE end_time <= $1",
                current_time,
            )

        if not records:
            return

        for record in records:
            user = guild.get_member(record["user_id"])
            role = guild.get_role(record["role_id"])

            if not user:
                continue

            if not role:
                continue

            if user.get_role(role.id) is None or not role:
                id_success.append(record["id"])
                continue

            try:
                await user.remove_roles(role)
                id_success.append(record["id"])
            except discord.HTTPException:
                logger.exception(
                    "Failed to remove temporary role",
                    extra={"user": user.id, "role": role.id},
                )

        async with self.db_pool.acquire() as conn:
            for ids in id_success:
                await conn.execute(
                    "DELETE FROM temp_role WHERE id = $1",
                    ids,
                )
            logger.info("Removed temporary roles", extra={"count": len(id_success)})

    @_check_temprole.before_loop
    async def _before_check_temprole(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Temporary(bot))
