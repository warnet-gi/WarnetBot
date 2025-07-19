import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.config import BLACKLIST_GA_ROLE_ID, GUILD_ID
from bot.helper import no_guild_alert

logger = logging.getLogger(__name__)


@commands.guild_only()
class Giveaway(commands.GroupCog, group_name="warnet-ga"):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        if not self._check_blacklist_ga.is_running():
            self._check_blacklist_ga.start()

    @app_commands.command(
        name="blacklist", description="Blacklist a user from giveaway"
    )
    @app_commands.describe(
        big="Yes if the giveaway is more than Rp50.000",
        winners="Discord IDs of the giveaway winner. Example: 1234567890,0987654321",
        ghosts="Member IDs who do not claim the giveaway. Example: 1234567890,0987654321",
    )
    async def add_giveaway_blacklist(  # noqa: C901, PLR0912, FIX002 # TODO: Improve this function
        self,
        interaction: Interaction,
        big: bool,
        winners: str,
        ghosts: str | None = None,
    ) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            return await no_guild_alert(interaction=interaction)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(
                "You are not an admin", ephemeral=True
            )

        winner_list: list[discord.Member] = []
        winners_list = winners.split(",")
        for winner in winners_list:
            if (user := interaction.guild.get_member(int(winner))) is None:
                return await interaction.followup.send(
                    f"User {winner} not found", ephemeral=True
                )
            winner_list.append(user)

        ghost_list: list[discord.Member] = []
        if ghosts:
            ghosts.split(",")
            for ghost in ghosts:
                if (user := interaction.guild.get_member(int(ghost))) is None:
                    return await interaction.followup.send(
                        f"User {ghost} not found", ephemeral=True
                    )
                ghost_list.append(user)

        if big:
            winner_day = 30
            ghosting_day = 15
        else:
            winner_day = 15
            ghosting_day = 7

        now = datetime.now(UTC)
        end_time_no_streak = now + timedelta(days=winner_day)
        end_time_streak = now + timedelta(days=winner_day * 2)
        end_time_ghosting = now + timedelta(days=ghosting_day)
        blacklist_role = interaction.guild.get_role(BLACKLIST_GA_ROLE_ID)
        if blacklist_role is None:
            logger.error(
                "Role not found",
                extra={"role_id": BLACKLIST_GA_ROLE_ID},
            )
            return None

        async with self.db_pool.acquire() as conn:
            streak_user_records = await conn.fetch(
                "SELECT user_id FROM blacklist_ga WHERE status_user = 1",
            )
            streak_user = {record["user_id"] for record in streak_user_records}

            for winner in winner_list:
                await winner.add_roles(blacklist_role)
                if winner.id in streak_user:
                    await conn.execute(
                        """
                        UPDATE blacklist_ga
                        SET end_time = $2, status_user = $3, cooldown_time = $4
                        WHERE user_id = $1
                        """,
                        winner.id,
                        end_time_streak,
                        0,
                        end_time_streak,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO blacklist_ga (user_id, end_time, status_user, cooldown_time) VALUES ($1, $2, $3, $4)",
                        winner.id,
                        end_time_no_streak,
                        1,
                        end_time_streak,
                    )
                logger.info(
                    "Added role blacklist role to winner",
                    extra={
                        "role_id": blacklist_role.id,
                        "winner_id": winner.id,
                        "winned_day": winner_day,
                    },
                )

            for ghost in ghost_list:
                await ghost.add_roles(blacklist_role)
                if ghost.id in streak_user:
                    await conn.execute(
                        "UPDATE blacklist_ga SET end_time = $2 WHERE user_id = $1",
                        ghost.id,
                        end_time_ghosting,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO blacklist_ga (user_id, end_time, status_user) VALUES ($1, $2, $3)",
                        ghost.id,
                        end_time_ghosting,
                        0,
                    )
                logger.info(
                    "Added role blacklist role to ghost",
                    extra={
                        "role_id": blacklist_role.id,
                        "winner_id": ghost.id,
                        "winned_day": winner_day,
                    },
                )

        embed = discord.Embed(
            title="Role Added",
            description=f"Successfully added the role {blacklist_role.mention} to the {len(winner_list)} winners and {len(ghost_list)} ghosts",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="List of Winners",
            value=f"{', '.join([winner.mention for winner in winner_list])}",
        )
        embed.add_field(
            name="List of Ghosts",
            value=f"{', '.join([ghost.mention for ghost in ghost_list])}",
        )
        return await interaction.followup.send(embed=embed)

    @tasks.loop(seconds=60)
    async def _check_blacklist_ga(self) -> None:
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            logger.error("Guild not found")
            return

        blacklist_role = guild.get_role(BLACKLIST_GA_ROLE_ID)
        if blacklist_role is None:
            logger.error("Blacklist role not found")
            return

        now = datetime.now(UTC)

        async with self.db_pool.acquire() as conn:
            user_want_remove = await conn.fetch(
                "SELECT user_id FROM blacklist_ga WHERE end_time <= $1 AND has_role = TRUE",
                now,
            )
            for user in user_want_remove:
                if user := guild.get_member(int(user["user_id"])):
                    await user.remove_roles(blacklist_role)
                    await conn.execute(
                        "UPDATE blacklist_ga SET has_role = FALSE WHERE user_id = $1",
                        user.id,
                    )
                    logger.info(
                        "Removed role  from user (rm role)",
                        extra={"role": blacklist_role.id, "user": user.id},
                    )

            user_want_delete = await conn.fetch(
                "SELECT user_id FROM blacklist_ga WHERE has_role = FALSE AND status_user = 0 OR cooldown_time <= $1",
                now,
            )
            for user in user_want_delete:
                if user:
                    await conn.execute(
                        "DELETE FROM blacklist_ga WHERE user_id = $1",
                        int(user["user_id"]),
                    )
                    logger.info("Deleted user (rm row table)", extra=user)

    @_check_blacklist_ga.before_loop
    async def _before_check_blacklist_ga(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Giveaway(bot))
