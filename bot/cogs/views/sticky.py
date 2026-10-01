# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalOperand=false, reportArgumentType=false, reportCallIssue=false
from datetime import UTC, datetime
from typing import Any

import discord
from discord import Interaction
from discord.ext import commands

from bot.helper import reject_non_author


class StickyPagination(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: float | None = 180,
        PreviousButton: discord.ui.Button | None = None,
        NextButton: discord.ui.Button | None = None,
        PageCounterStyle: discord.ButtonStyle = discord.ButtonStyle.grey,
        initial_page_number: int = 0,
        ephemeral: bool = False,
        list_data: list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=timeout)

        # one Button attaches to one View only; defaults would be shared across instances
        if PreviousButton is None:
            PreviousButton = discord.ui.Button(
                emoji=discord.PartialEmoji(name="\U000025c0"),
            )
        if NextButton is None:
            NextButton = discord.ui.Button(
                emoji=discord.PartialEmoji(name="\U000025b6"),
            )

        self.PreviousButton = PreviousButton
        self.NextButton = NextButton
        self.PageCounterStyle = PageCounterStyle
        self.initial_page_number = initial_page_number
        self.ephemeral = ephemeral
        self.list_data = list_data

        self.pages: list[discord.Embed] = []
        self.page_counter: discord.ui.Button = None
        self.current_page: int = 0
        self.total_page_count: int = 0
        self.ctx = None
        self.message = None

    async def construct_pages(
        self, ctx: commands.Context, list_data: list[dict[str, Any]]
    ) -> None:
        N_LIST = 20

        total_data = len(list_data)
        if total_data % N_LIST:
            self.total_page_count = total_data // N_LIST + 1
        else:
            self.total_page_count = total_data // N_LIST

        # empty list still renders one page; keep label/wrap math sane (1/1, no IndexError)
        if not self.total_page_count:
            self.total_page_count = 1

        if self.total_page_count:
            for page_num in range(self.total_page_count):
                page_data_list = [
                    list_data[(page_num * N_LIST) : (page_num * N_LIST) + N_LIST // 2],
                    list_data[
                        (page_num * N_LIST) + N_LIST // 2 : (page_num + 1) * N_LIST
                    ],
                ]

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    title="STICKY MESSAGE",
                    description=f"**Sticky Messages in {ctx.guild.name}**",
                    timestamp=datetime.now(UTC),
                )

                for sticky_data_list in page_data_list:
                    if (
                        sticky_data_list == page_data_list[1]
                        and len(page_data_list[1]) == 0
                    ):
                        continue

                    field_value = ""
                    field_name = ""

                    if sticky_data_list == page_data_list[0]:
                        field_name = "Channel/Thread Name"
                    else:
                        field_name = "_ _"

                    for sticky_data in sticky_data_list:
                        row_string = f"<#{sticky_data['channel_id']}>\n"
                        field_value += row_string

                    embed.add_field(name=field_name, value=field_value)

                embed.set_footer(
                    text=f"{self.ctx.author.name}",
                    icon_url=self.ctx.author.display_avatar.url,
                )
                self.pages.append(embed)

        else:
            embed = discord.Embed(
                color=discord.Color.gold(),
                title="STICKY MESSAGE",
                description="**NO STICKY MESSAGE IN THIS SERVER**",
                timestamp=datetime.now(UTC),
            )

            embed.set_footer(
                text=f"{self.ctx.author.name}",
                icon_url=self.ctx.author.display_avatar.url,
            )
            self.pages.append(embed)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        # message may be deleted or never attached; teardown must never raise
        if self.message is None:
            self.stop()
            return
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
        self.stop()

    async def start(self, ctx: Interaction | commands.Context) -> None:
        if isinstance(ctx, Interaction):
            ctx = await commands.Context.from_interaction(ctx)
        self.ctx = ctx

        await self.construct_pages(self.ctx, self.list_data)
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
        # single page (incl. empty list) has nowhere to navigate
        if self.total_page_count <= 1:
            self.PreviousButton.disabled = True
            self.NextButton.disabled = True
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
        if await reject_non_author(interaction, self.ctx.author):
            return

        await self.next()
        await interaction.response.defer()

    async def previous_button_callback(self, interaction: Interaction) -> None:
        if await reject_non_author(interaction, self.ctx.author):
            return

        await self.previous()
        await interaction.response.defer()
