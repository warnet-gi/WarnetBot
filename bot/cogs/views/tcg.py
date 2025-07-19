from typing import Any

import discord
from discord import Interaction
from discord.ext import commands

from bot import config
from bot.helper import no_guild_alert


class LeaderboardPagination(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: float | None = 180,
        previousbutton: discord.ui.Button | None = None,
        nextbutton: discord.ui.Button | None = None,
        pagecounterstyle: discord.ButtonStyle = discord.ButtonStyle.grey,
        initial_page_number: int = 0,
        ephemeral: bool = False,
        leaderboard_data: list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=timeout)

        if not nextbutton:
            nextbutton = discord.ui.Button(
                emoji=discord.PartialEmoji(name="\U000025b6")
            )

        if not previousbutton:
            previousbutton = discord.ui.Button(
                emoji=discord.PartialEmoji(name="\U000025c0")
            )

        self.PreviousButton = previousbutton
        self.NextButton = nextbutton
        self.PageCounterStyle = pagecounterstyle
        self.initial_page_number = initial_page_number
        self.ephemeral = ephemeral
        self.leaderboard_data = leaderboard_data

        self.pages: list[discord.Embed] = []

    async def construct_pages(  # noqa: C901, PLR0912, PLR0915, FIX002 #TODO: improve this
        self, ctx: commands.Context, leaderboard_data: list[dict[str, Any]]
    ) -> None:
        # Pick only N members per embed
        n_members = 20

        if not ctx.guild:
            await no_guild_alert(ctx=ctx)
            return

        total_data = len(leaderboard_data)
        if total_data % n_members:
            self.total_page_count = total_data // n_members + 1
        else:
            self.total_page_count = total_data // n_members

        title_emoji = config.TCGConfig.TCG_TITLE_EMOJI
        rank_count = 1
        author_rank = 0

        if self.total_page_count:
            for page_num in range(self.total_page_count):
                page_member_data_list = [
                    leaderboard_data[
                        (page_num * n_members) : (page_num * n_members) + n_members // 2
                    ],
                    leaderboard_data[
                        (page_num * n_members) + n_members // 2 : (page_num + 1)
                        * n_members
                    ],
                ]

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    title="WARNET TCG ELO RATING LEADERBOARD",
                    description="**Berikut rank ELO tertinggi di server WARNET**",
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/929746553944551424/1052431858371133460/Paimon_TCG.png"
                )

                for member_data_list in page_member_data_list:
                    if (
                        member_data_list == page_member_data_list[1]
                        and len(page_member_data_list[1]) == 0
                    ):
                        continue

                    field_value = ""
                    field_name = (
                        "Rank  |  Player  |  W/L  |  ELO"
                        if member_data_list == page_member_data_list[0]
                        else "|"
                    )
                    for member_data in member_data_list:
                        member = ctx.guild.get_member(member_data["discord_id"])
                        # Prevent none object if user leaves the guild but they still in the leaderboard
                        if not member:
                            member = await ctx.bot.fetch_user(member_data["discord_id"])

                        if len(member.name) > n_members / 2:
                            member_name = member.name[:7] + "..."
                        else:
                            member_name = member.name

                        member_title_emoji = (
                            title_emoji[member_data["title"]]
                            if member_data["title"]
                            else ""
                        )
                        row_string = f"`{rank_count:>2}` {member_title_emoji:<1} {discord.utils.escape_markdown(text=member_name):<10} ({member_data['win_count']:>2}/{member_data['loss_count']:<2}) **{member_data['elo']:.1f}**\n"
                        field_value += row_string

                        if member.id == self.ctx.author.id:
                            author_rank = rank_count

                        rank_count += 1

                    embed.add_field(name=field_name, value=field_value)
                    if not self.ctx.author.avatar:
                        icon_url = None
                    else:
                        icon_url = self.ctx.author.avatar.url
                    embed.set_footer(
                        text=f"{self.ctx.author.name}",
                        icon_url=icon_url,
                    )
                self.pages.append(embed)

        # Null leaderboard
        else:
            embed = discord.Embed(
                color=discord.Color.gold(),
                title="WARNET TCG ELO RATING LEADERBOARD",
                description="**Berikut rank ELO tertinggi di server WARNET**",
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/929746553944551424/1052431858371133460/Paimon_TCG.png"
            )
            embed.add_field(
                name="Rank  |  Player  |  W/L  |  ELO",
                value="**NO PLAYER IN THIS LEADERBOARD YET**",
            )
            if not self.ctx.author.avatar:
                icon_url = None
            else:
                icon_url = self.ctx.author.avatar.url
            embed.set_footer(text=f"{self.ctx.author.name}", icon_url=icon_url)
            self.pages.append(embed)

        for embed in self.pages:
            if author_rank:
                embed.set_footer(
                    text=f"{len(leaderboard_data)} members has been listed in this leaderboard. You are in rank #{author_rank}."
                )
            else:
                embed.set_footer(
                    text=f"{len(leaderboard_data)} members has been listed in this leaderboard. You are not in the leaderboard yet. "
                    "Register and play at least 1 official TCG WARNET Tournament match to enter the leaderboard."
                )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def start(self, ctx: Interaction | commands.Context) -> None:
        if isinstance(ctx, Interaction):
            ctx = await commands.Context.from_interaction(ctx)
        self.ctx = ctx

        await self.construct_pages(self.ctx, self.leaderboard_data)
        self.current_page = self.initial_page_number
        self.page_counter = discord.ui.Button(
            label=f"{self.initial_page_number + 1}/{self.total_page_count}",
            style=self.PageCounterStyle,
            disabled=True,
        )

        self.PreviousButton.callback = self.previous_button_callback
        self.NextButton.callback = self.next_button_callback
        self.PreviousButton.disabled = False
        self.NextButton.disabled = False
        self.add_item(self.PreviousButton)
        self.add_item(self.page_counter)
        self.add_item(self.NextButton)

        self.message = await ctx.send(
            embed=self.pages[self.initial_page_number],
            view=self,
            ephemeral=self.ephemeral,
        )

    async def next(self) -> None:
        if self.current_page == self.total_page_count - 1:
            self.current_page = 0
        else:
            self.current_page += 1

        self.page_counter.label = f"{self.current_page + 1}/{self.total_page_count}"
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def previous(self) -> None:
        if self.current_page == 0:
            self.current_page = self.total_page_count - 1
        else:
            self.current_page -= 1

        self.page_counter.label = f"{self.current_page + 1}/{self.total_page_count}"
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def next_button_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                description="You cannot control this pagination because you did not execute it.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await self.next()
        await interaction.response.defer()
        return

    async def previous_button_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                description="You cannot control this pagination because you did not execute it.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await self.previous()
        await interaction.response.defer()
        return
