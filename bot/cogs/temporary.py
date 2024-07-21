import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from bot.bot import WarnetBot
from bot.cogs.ext.temprole.time import parse_time_string
from bot.config import GUILD_ID

logger = logging.getLogger(__name__)


@commands.guild_only()
class Temporary(commands.GroupCog, group_name='warnet-temp'):
    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._check_temprole.start()

    @app_commands.command(name='add', description='Adds a temprole to user')
    @app_commands.describe(
        user='User to add temprole to',
        duration='Duration of temprole',
        role='Role to add',
    )
    async def give_role_on_poll(
        self,
        interaction: Interaction,
        user: discord.Member,
        duration: str,
        role: discord.Role,
    ) -> None:
        await interaction.response.defer()
        try:
            duration_seconds = parse_time_string(duration)
            if duration_seconds < 60:
                return await interaction.followup.send(
                    'Duration must be at least 1 minute', ephemeral=True
                )
            await user.add_roles(role)
        except ValueError:
            return await interaction.followup.send('Invalid duration format', ephemeral=True)
        except:
            return await interaction.followup.send(f'Something went wrong', ephemeral=True)

        logger.info(f'Added role {role} to user {user.id} for {duration_seconds} seconds')
        total_duration = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO temp_role (user_id, role_id, end_time) VALUES ($1, $2, $3)',
                user.id,
                role.id,
                total_duration,
            )

        embed = discord.Embed(
            title="Role Added",
            description=f"Successfully added the role {role.mention} to the {user.mention}\nremove <t:{int(total_duration.timestamp())}:R>",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)

    @tasks.loop(seconds=60)
    async def _check_temprole(self) -> None:
        current_time = datetime.now(timezone.utc)
        guild = self.bot.get_guild(GUILD_ID)
        user_success = []

        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                'SELECT user_id, role_id FROM temp_role WHERE end_time <= $1',
                current_time,
            )

        for record in records:
            try:
                user = guild.get_member(int(record['user_id']))
                role = guild.get_role(int(record['role_id']))

                if user and role:
                    await user.remove_roles(role)
                    user_success.append(user.id)
            except Exception:
                pass

        for user in user_success:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    'DELETE FROM temp_role WHERE user_id = $1',
                    user,
                )
            logger.info(
                f'Removed role {role.id} from {user} users'
            )

    @_check_temprole.before_loop
    async def _before_check_temprole(self):
        await self.bot.wait_until_ready()


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Temporary(bot))
