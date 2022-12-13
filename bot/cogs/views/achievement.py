import datetime

import discord
from discord import Interaction
from discord.ext import commands

from typing import Optional, Dict


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Ya', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
    
    @discord.ui.button(label='Tidak', style=discord.ButtonStyle.primary)
    async def cancel(self, interaction: Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()


class StatsProgressDetail(discord.ui.View):
    def __init__(self, *,
                 timeout: int = 60,
                 PreviousButton: discord.ui.Button = discord.ui.Button(emoji=discord.PartialEmoji(name="\U000025c0")),
                 NextButton: discord.ui.Button = discord.ui.Button(emoji=discord.PartialEmoji(name="\U000025b6")),
                 PageCounterStyle: discord.ButtonStyle = discord.ButtonStyle.grey,
                 InitialPage: int = 0,
                 InitialEmbed: discord.Embed,
                 completed_achievement_list: list[int],
                 achievement_data: Dict[str, Dict[str, str]],
                 Member: Optional[discord.Member],
                 ephemeral: bool = False) -> None:
        
        self.CheckStatsDetailButton = discord.ui.Button(
            label='Stats Details',
            style=discord.ButtonStyle.primary
        )
        self.SummaryButton = discord.Button = discord.ui.Button(
            label='Summary',
            style=discord.ButtonStyle.primary
        )
        self.PreviousButton = PreviousButton
        self.NextButton = NextButton
        
        self.PageCounterStyle = PageCounterStyle
        self.InitialPage = InitialPage
        self.InitialEmbed = InitialEmbed
        self.completed_achievement_list = completed_achievement_list
        self.achievement_data = achievement_data
        self.Member = Member
        self.ephemeral = ephemeral

        self.pages = None
        self.ctx = None
        self.message = None
        self.current_page = None
        self.page_counter = None
        self.total_page_count = None

        super().__init__(timeout=timeout)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def start(self, ctx: Interaction|commands.Context) -> None:
        if isinstance(ctx, Interaction):
            ctx = await commands.Context.from_interaction(ctx)
        self.ctx = ctx

        self.PreviousButton.callback = self.previous_button_callback
        self.NextButton.callback = self.next_button_callback
        self.CheckStatsDetailButton.callback = self.check_stats_detail_callback
        self.SummaryButton.callback = self.stats_summary_callback

        self.add_item(self.CheckStatsDetailButton)

        self.message = await ctx.send(embed=self.InitialEmbed, view=self, ephemeral=self.ephemeral)

    async def previous(self) -> None:
        if self.current_page == 0:
            self.current_page = self.total_page_count - 1
        else:
            self.current_page -= 1

        self.page_counter.label = f"{self.current_page + 1}/{self.total_page_count}"
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def next(self) -> None:
        if self.current_page == self.total_page_count - 1:
            self.current_page = 0
        else:
            self.current_page += 1

        self.page_counter.label = f"{self.current_page + 1}/{self.total_page_count}"
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def check_stats_detail(self) -> None:
        total_data = len(self.achievement_data)
        total_pages = total_data//10 + 1 if total_data % 10 else total_data//10

        embeds = []
        mention_text = self.Member.name+"'s" if self.Member != None else 'Your'
        for page in range(total_pages):
            embed = discord.Embed(
                color=0xfcba03,
                title=f"{mention_text} Achievement List",
                description='Berikut daftar achievement yang sudah diselesaikan:',
                timestamp=datetime.datetime.now()
            )

            id_start = 10*page + 1
            id_end = 10*(page+1)
            for achievement_id in range(id_start, id_end+1):
                data = self.achievement_data[str(achievement_id)]
                is_complete_emoji = '✅' if achievement_id in self.completed_achievement_list else '❌'
                embed.add_field(name=f"🏅`{achievement_id}` {data['name']} {is_complete_emoji}", value=f"```{data['desc']}```", inline=False)

            embeds.append(embed)
        
        # Initiate pagination
        self.pages = embeds
        self.total_page_count = len(self.pages)
        self.current_page = self.InitialPage
        self.page_counter = discord.ui.Button(
            label=f"{self.InitialPage + 1}/{self.total_page_count}",
            style=self.PageCounterStyle,
            disabled=True
        )

        self.remove_item(self.CheckStatsDetailButton)
        self.add_item(self.PreviousButton)
        self.add_item(self.page_counter)
        self.add_item(self.NextButton)
        self.add_item(self.SummaryButton)

        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def stats_summary(self) -> None:
        self.add_item(self.CheckStatsDetailButton)
        self.remove_item(self.PreviousButton)
        self.remove_item(self.page_counter)
        self.remove_item(self.NextButton)
        self.remove_item(self.SummaryButton)
        
        await self.message.edit(embed=self.InitialEmbed, view=self)

    async def next_button_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(description="You cannot control this pagination because you did not execute it.",
                                  color=discord.Colour.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.next()
        await interaction.response.defer()

    async def previous_button_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(description="You cannot control this pagination because you did not execute it.",
                                  color=discord.Colour.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.previous()
        await interaction.response.defer()

    async def check_stats_detail_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(description="You cannot control this pagination because you did not execute it.",
                                  color=discord.Colour.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.check_stats_detail()
        await interaction.response.defer()

    async def stats_summary_callback(self, interaction: Interaction) -> None:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(description="You cannot control this pagination because you did not execute it.",
                                  color=discord.Colour.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.stats_summary()
        await interaction.response.defer()
