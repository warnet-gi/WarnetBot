import discord
from discord import Interaction, app_commands, Embed
from discord.ext import commands

from typing import Optional, Union

from bot.bot import WarnetBot
from bot.config import config
from bot.cogs.ext.tcg.admin import (
    register_member,
    unregister_member,
    reset_member_stats,
    reset_all_member_stats,
    set_match_result,
    undo_match_result,
    set_member_stats
)
from bot.cogs.ext.tcg.member import (
    register,
    member_stats,
    leaderboard,
)

GUILD_ID = config.GUILD_ID
DEV_GUILD_ID = config.DEV_GUILD_ID

@commands.guild_only()
class TCG(commands.GroupCog, group_name="warnet-tcg"):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.match_history = []

    @app_commands.command(name='register', description='Member need to register before using other tcg commands.')
    async def tcg_register(self, interaction: Interaction) -> None:
        await register(self, interaction)

    @app_commands.command(name='register-member', description='Administrator can register a member manually if they haven\'t registered yet.')
    @app_commands.describe(member='Member that you want to register.')
    async def tcg_register_member(self, interaction: Interaction, member: Union[discord.Member, discord.User]) -> None:
        await register_member(self, interaction, member)

    @app_commands.command(name='unregister-member', description='Administrator can unregister a member from TCG leaderboard.')
    @app_commands.describe(member='Member that you want to unregister.')
    async def tcg_unregister_member(self, interaction: Interaction, member: Union[discord.Member, discord.User]) -> None:
        await unregister_member(self, interaction, member)

    @app_commands.command(name='member-stats', description='Member can check their or someone else\'s TCG stats.')
    @app_commands.describe(member='Member that you want to look at.')
    async def tcg_member_stats(self, interaction: Interaction, member: Optional[Union[discord.Member, discord.User]]) -> None:
        await member_stats(self, interaction, member)

    @app_commands.command(name='leaderboard', description='ELO leaderboard for WARNET TCG.')
    async def tcg_leaderboard(self, interaction: Interaction) -> None:
        await leaderboard(self, interaction)

    @app_commands.command(name='reset-stats', description='Reset a member TCG stats.')
    @app_commands.describe(member='Member that you want to reset their stats.')
    async def tcg_reset_member_stats(self, interaction: Interaction, member: Union[discord.Member, discord.User]) -> None:
        await reset_member_stats(self, interaction, member)

    @app_commands.command(name='reset-all-stats', description='Reset all member TCG stats.')
    async def tcg_reset_all_member_stats(self, interaction: Interaction) -> None:
        await reset_all_member_stats(self, interaction)

    @app_commands.command(name='set-match-result', description='Set the TCG match result between players.')
    @app_commands.describe(winner='Member who won a match.', loser='Member who lose a match.')
    async def tcg_set_match_result(
        self,
        interaction: Interaction,
        winner: Union[discord.Member, discord.User],
        loser: Union[discord.Member, discord.User]
    ) -> None:
        await set_match_result(self, interaction, winner, loser)

    @app_commands.command(name='set-member-stats', description='Set tcg stats for a member manually.')
    @app_commands.describe(
        member='Member that you want to set their stat.',
        win_count='Win count value with 0 as the minimum value.',
        loss_count='Loss count value with 0 as the minimum value.',
        elo_rating='ELO rating value with 0 as the minimum value.'
    )
    async def tcg_set_member_stats(
        self,
        interaction: Interaction,
        member: Union[discord.Member, discord.User],
        win_count: Optional[app_commands.Range[int, 0]],
        loss_count: Optional[app_commands.Range[int, 0]],
        elo_rating: Optional[app_commands.Range[float, 0]]
    ) -> None:
        await set_member_stats(self, interaction, member, win_count, loss_count, elo_rating)

    @app_commands.command(name='undo-match-result', description='Undo the TCG match result between players.')
    @app_commands.describe(member='Member that you want to revert their result against other members previously.',)
    async def tcg_undo_match_result(self, interaction: Interaction, member: Union[discord.Member, discord.User]) -> None:
        await undo_match_result(self, interaction, member)

    @app_commands.command(name='rules', description='Return TCG WARNET OPEN ruleset document link.')
    async def tcg_rules(self, interaction: Interaction) -> None:
        await interaction.response.send_message(
            content="Silakan membaca ruleset TCG WARNET OPEN pada link berikut:\n**https://s.id/TCG-WARNET-RULESET**"
        )

async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(
        TCG(bot),
        guilds=[discord.Object(DEV_GUILD_ID), discord.Object(GUILD_ID)]
    )