from datetime import UTC, datetime
from typing import Any

import discord
from discord import Interaction
from discord.ext import commands


class StickyPagination(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: float | None = 180,
        previousbutton: discord.ui.Button | None = None,
        nextbutton: discord.ui.Button | None = None,
        pagecounterstyle: discord.ButtonStyle = discord.ButtonStyle.grey,
        initial_page_number: int = 0,
        ephemeral: bool = False,
        list_data: list[dict[str, Any]],
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
        self.list_data = list_data

        self.pages: list[discord.Embed] = []

    async def construct_pages(self, list_data: list[dict[str, Any]]) -> None:  # noqa: PLR0912, FIX002 #TODO: Improve this
        n_list = 10

        total_data = len(list_data)
        if total_data % n_list:
            self.total_page_count = total_data // n_list + 1
        else:
            self.total_page_count = total_data // n_list

        if self.total_page_count:
            for page_num in range(self.total_page_count):
                page_data_list = [
                    list_data[(page_num * n_list) : (page_num * n_list) + n_list // 2],
                    list_data[
                        (page_num * n_list) + n_list // 2 : (page_num + 1) * n_list
                    ],
                ]

                embed = discord.Embed(
                    color=discord.Color.gold(),
                    title="WARNET STICKY MESSAGE",
                    description="**Sticky message yang terdapat pada server WARNET**",
                    timestamp=datetime.now(tz=UTC),
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

                if not self.ctx.author.avatar:
                    icon_url = None
                else:
                    icon_url = self.ctx.author.avatar.url
                embed.set_footer(text=f"{self.ctx.author.name}", icon_url=icon_url)
                self.pages.append(embed)

        else:
            embed = discord.Embed(
                color=discord.Color.gold(),
                title="WARNET STICKY MESSAGE",
                description="**NO STICKY MESSAGE IN THIS SERVER**",
                timestamp=datetime.now(tz=UTC),
            )
            if not self.ctx.author.avatar:
                icon_url = None
            else:
                icon_url = self.ctx.author.avatar.url
            embed.set_footer(text=f"{self.ctx.author.name}", icon_url=icon_url)
            self.pages.append(embed)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def start(self, ctx: Interaction | commands.Context) -> None:
        if isinstance(ctx, Interaction):
            ctx = await commands.Context.from_interaction(ctx)
        self.ctx = ctx

        await self.construct_pages(self.list_data)
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
                description="You can't control this pagination because you did not execute it.",
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
                description="You can't control this pagination because you did not execute it.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await self.previous()
        await interaction.response.defer()
        return
