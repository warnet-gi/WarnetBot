import discord
from discord import Interaction
from discord.ext import commands

from typing import Optional, Any


class BuronanPagination(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: Optional[float] = 180,
        PreviousButton: discord.ui.Button = discord.ui.Button(
            emoji=discord.PartialEmoji(name="\U000025c0")
        ),
        NextButton: discord.ui.Button = discord.ui.Button(
            emoji=discord.PartialEmoji(name="\U000025b6")
        ),
        PageCounterStyle: discord.ButtonStyle = discord.ButtonStyle.grey,
        initial_page_number: int = 0,
        ephemeral: bool = False,
        buronan_list_data: list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=timeout)

        self.PreviousButton = PreviousButton
        self.NextButton = NextButton
        self.PageCounterStyle = PageCounterStyle
        self.initial_page_number = initial_page_number
        self.ephemeral = ephemeral
        self.buronan_list_data = buronan_list_data

        self.pages: list[discord.Embed] = []
        self.page_counter: discord.ui.Button = None
        self.current_page = None
        self.total_page_count = None
        self.ctx = None
        self.message = None

    async def construct_pages(
        self, ctx: commands.Context, buronan_list_data: list[dict[str, Any]]
    ) -> None:
        # Pick only N members per embed
        N_MEMBERS = 10

        total_data = len(buronan_list_data)
        if total_data % N_MEMBERS:
            self.total_page_count = total_data // N_MEMBERS + 1
        else:
            self.total_page_count = total_data // N_MEMBERS

        if self.total_page_count:
            for page_num in range(self.total_page_count):
                page_member_data_list = [
                    buronan_list_data[
                        (page_num * N_MEMBERS) : (page_num * N_MEMBERS) + N_MEMBERS // 2
                    ],
                    buronan_list_data[
                        (page_num * N_MEMBERS) + N_MEMBERS // 2 : (page_num + 1) * N_MEMBERS
                    ],
                ]

                embed = discord.Embed(
                    color=discord.Color.dark_theme(),
                    title='DAFTAR BURONAN KHAENRIAH',
                    description=f'**Berikut daftar buronan dengan level warning nya di server {ctx.guild.name}**',
                )
                embed.set_thumbnail(
                    url='https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png'
                )

                for member_data_list in page_member_data_list:
                    if (
                        member_data_list == page_member_data_list[1]
                        and len(page_member_data_list[1]) == 0
                    ):
                        continue

                    field_value = ''
                    field_name = (
                        'Warning Level  |  Member'
                        if member_data_list == page_member_data_list[0]
                        else '|'
                    )
                    for member_data in member_data_list:
                        member = ctx.guild.get_member(member_data['discord_id'])
                        # Prevent none object if user leaves the guild but they still in the list
                        if not member:
                            member = await ctx.bot.fetch_user(member_data['discord_id'])

                        row_string = f"`{member_data['warn_level']:>2}` {discord.utils.escape_markdown(text=str(member))}\n"
                        field_value += row_string

                    embed.add_field(name=field_name, value=field_value)

                self.pages.append(embed)

        # Null list
        else:
            embed = discord.Embed(
                color=discord.Color.dark_theme(),
                title='DAFTAR BURONAN KHAENRIAH',
                description=f'**Berikut daftar buronan dengan level warning di server {ctx.guild.name}**',
            )
            embed.set_thumbnail(
                url='https://media.discordapp.net/attachments/918150951204945950/1081450017065275454/skull.png'
            )
            embed.add_field(
                name='Warning Level  |  Member',
                value='**NO MEMBER IN THIS LIST YET**',
            )
            self.pages.append(embed)

        for embed in self.pages:
            embed.set_footer(text=f'{len(buronan_list_data)} members has been listed in this list.')

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def start(self, ctx: Interaction | commands.Context) -> None:
        if isinstance(ctx, Interaction):
            ctx = await commands.Context.from_interaction(ctx)
        self.ctx = ctx

        await self.construct_pages(self.ctx, self.buronan_list_data)
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
            embed=self.pages[self.initial_page_number], view=self, ephemeral=self.ephemeral
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
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.next()
        await interaction.response.defer()

    async def previous_button_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                description="You cannot control this pagination because you did not execute it.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.previous()
        await interaction.response.defer()
