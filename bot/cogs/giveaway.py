import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.config import GiveawayConfig, GUILD_ID

logger = logging.getLogger(__name__)


@commands.guild_only()
class Giveaway(commands.GroupCog, group_name='warnet-ga'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._check_blacklist_ga.start()

    @app_commands.command(name='blacklist', description='Blacklist a user from giveaway')
    @app_commands.describe(
        amount='Amount of giveaway. Example: 50000',
        winner='Winner of the giveaway. Example: 1234567890,0987654321',
        ghosting='the ghost. Example: 1234567890,0987654321',
    )
    async def add_giveaway_blacklist(
        self,
        interaction: Interaction,
        amount: int,
        winner: str,
        ghosting: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()
        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send('You are not an admin', ephemeral=True)

        winnerss: list[discord.Member] = []
        winners = winner.split(',')
        for win in winners:
            user = interaction.guild.get_member(int(win))
            if user is None:
                return await interaction.followup.send(f'User {win} not found', ephemeral=True)
            winnerss.append(user)

        ghostss: list[discord.Member] = []
        if ghosting:
            ghosts = ghosting.split(',')
            for ghost in ghosts:
                user = interaction.guild.get_member(ghost)
                if user is None:
                    return await interaction.followup.send(
                        f'User {ghost} not found', ephemeral=True
                    )
                ghostss.append(user)

        if amount < GiveawayConfig.BIG_GIVEAWAY:
            winner_day: 15
            ghosting_day: 7
        else:
            winner_day: 30
            ghosting_day: 15
        end_time_no_streak = datetime.now(timezone.utc) + timedelta(days=winner_day)
        end_time_streak = datetime.now(timezone.utc) + timedelta(days=winner_day * 2)
        blacklist_role = interaction.guild.get_role(GiveawayConfig.BLACKLIST_ROLE_ID)

        async with self.db_pool.acquire() as conn:
            streak_user = await conn.fetch(
                'SELECT user_id FROM black_ga WHERE status_user = 1',
            )

            for winn in winnerss:
                await winn.add_roles(blacklist_role)
                if win in streak_user:
                    await conn.execute(
                        'UPDATE black_ga SET (end_time, status_user) VALUES ($2, $3) WHERE user_id = $1',
                        winn.id,
                        end_time_streak,
                        3,
                    )
                else:
                    await conn.execute(
                        'INSERT INTO black_ga (user_id, end_time, status_user) VALUES ($1, $2, $3)',
                        winn.id,
                        end_time_no_streak,
                        1,
                    )
            logger.info(f'Added role {blacklist_role.id} to user {winn.id} for {winner_day} days')

        for ghost in ghostss:
            await ghost.add_roles(blacklist_role)
            end_time = datetime.now(timezone.utc) + timedelta(days=ghosting_day)
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    'INSERT INTO black_ga (user_id, end_time, status_user) VALUES ($1, $2, $3)',
                    ghost.id,
                    end_time,
                    2,
                )
            logger.info(
                f'Added role {blacklist_role.id} to user {ghost.id} for {ghosting_day} days'
            )

        embed = discord.Embed(
            title="Role Added",
            description=f"Successfully added the role {blacklist_role.mention} to the {len(winnerss)} winners and {len(ghostss)} ghosts",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="List of Winners",
            value=f"{', '.join([winner.mention for winner in winnerss])}",
        )
        embed.add_field(
            name="List of Ghosts",
            value=f"{', '.join([ghost.mention for ghost in ghostss])}",
        )
        await interaction.followup.send(embed=embed)

    @tasks.loop(seconds=60)
    async def _check_blacklist_ga(self) -> None:
        guild = self.bot.get_guild(GUILD_ID)

        async with self.db_pool.acquire() as conn:
            user_want_remove = await conn.fetch(
                'SELECT user_id FROM black_ga WHERE end_time <= $1 AND has_role = TRUE',
                datetime.now(timezone.utc) - timedelta(days=30),
            )

            for user in user_want_remove:
                user = guild.get_member(int(user['user_id']))
                if user:
                    blacklist_role = guild.get_role(GiveawayConfig.BLACKLIST_ROLE_ID)
                    await user.remove_roles(blacklist_role)
                    await conn.execute(
                        'UPDATE black_ga SET has_role = FALSE WHERE user_id = $1',
                        user.id,
                    )
                    logger.info(f'Removed role {blacklist_role.id} from user {user.id} (rm role)')

        async with self.db_pool.acquire() as conn:
            user_want_delete = await conn.fetch(
                'SELECT user_id FROM black_ga WHERE AND has_role = FALSE AND status_user != 1',
            )

            for user in user_want_delete:
                if user:
                    await conn.execute(
                        'DELETE FROM black_ga WHERE user_id = $1',
                        int(user['user_id']),
                    )
                    logger.info(f'Deleted user {user.id} (rm row table)')

    @_check_blacklist_ga.before_loop
    async def _before_check_blacklist_ga(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Giveaway(bot))
