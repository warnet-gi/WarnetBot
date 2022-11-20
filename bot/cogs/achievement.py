import Paginator
import discord
from discord import Interaction, app_commands, Embed
from discord.ext import commands

import json
import datetime
from typing import List, Dict, Optional
from asyncpg.exceptions import UniqueViolationError

from bot.bot import WarnetBot
from bot.config import config


ACHIEVEMENT_DATA_PATH = 'bot/data/achievement.json'

class Achievement(commands.Cog):

    def __init__(self, bot: WarnetBot) -> None:
        self.bot = bot
        self.db_pool = bot.get_db_pool()
        self.achievement_data = self.get_achievement_json_data()
        self._total_achievement_data = len(self.achievement_data)
        self.achievement_embeds = self.prepare_achievement_embeds()

    @app_commands.command(name='achievement-member-register', description='Member need to register before using other achievement commands')
    async def achievement_register(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        author_id = interaction.user.id
        embed: discord.Embed
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", author_id)
            if res == None:
                await conn.execute("INSERT INTO warnet_user(discord_id) VALUES ($1);", author_id)
                embed = discord.Embed(
                    color=discord.Colour.green(),
                    title='✅ Registered successfully',
                    description=f"""
                    Sekarang kamu sudah bisa melakukan proses claim achievement dan cek progress di </achievement-stats:0>.
                    Hubungi <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> untuk claim achievement.
                    """,
                    timestamp=datetime.datetime.now()
                )
            else:
                embed = discord.Embed(
                    color=discord.Colour.red(),
                    title='❌ You are already registered',
                    description="Akun kamu sudah terdaftar. Tidak perlu mendaftar lagi.",
                    timestamp=datetime.datetime.now()
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='achievement-list', description='Shows all available achievement list')
    async def achievement_list(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        await Paginator.Simple().start(interaction, pages=self.achievement_embeds)

    @app_commands.command(name='achievement-detail', description='Shows the detail of an achievement')
    async def achievement_detail(self, interaction: Interaction, achievement_id: int) -> None:
        await interaction.response.defer()
        
        try:
            target_data = self.achievement_data[str(achievement_id)]

        # Handle undefined key
        except KeyError:
            error_embed = discord.Embed(
                color=discord.Colour.red(),
                title='❌ Achievement not found',
                description='Cobalah untuk memeriksa apakah id yang diinput sudah benar. Ketik </achievement-list:0> untuk melihat daftar achievement yang tersedia.',
                timestamp=datetime.datetime.now(),
            )
            await interaction.followup.send(embed=error_embed)
            return
        
        name = target_data['name']
        desc = target_data['desc']
        claim = target_data['claim']

        author_color = interaction.user.color
        embed = discord.Embed(
            color=author_color,
            title=f'🏅 {name}',
            description=desc,
            timestamp=datetime.datetime.now(),
        )
        embed.add_field(
            name="How to claim?",
            value=f"{claim}.\nHubungi <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> untuk claim achievement."
        )
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/761684443915485184/956797958651805716/paimon_win.gif')
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='achievement-stats', description='Shows your completed achievement stats')
    async def achievement_stats(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        author_id = interaction.user.id
        author_name = interaction.user.name
        author_color = interaction.user.color 
        async with self.db_pool.acquire() as conn:
            res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", author_id)
            if res == None:
                embed = discord.Embed(
                    color=discord.Colour.red(),
                    title='❌ User not registered',
                    description=f"<@{author_id}> belum terdaftar di database. Silakan <@{author_id}> untuk mendaftar terlebih dahulu menggunakan </achievement-member-register:0>",
                    timestamp=datetime.datetime.now()
                )

                await interaction.followup.send(embed=embed)

            else:
                total_completed = await conn.fetchval("SELECT COUNT(*) FROM achievement_progress WHERE discord_id = $1;", author_id)
                records = await conn.fetch("SELECT achievement_id FROM achievement_progress WHERE discord_id = $1 ORDER BY achievement_id ASC;", author_id)
                completed_achievement_list = [dict(row)['achievement_id'] for row in records]  # [1, 2, 3]

                # TODO: shows total completed, shows list of completed achievement (use pagination)
                stats_percentage = (total_completed / len(self.achievement_data)) * 100
                badge_id = self.get_achievement_badge_id(total_completed) 
                embed = discord.Embed(
                    color=author_color,
                    title=f"🏆 {author_name}'s Achievement Progress",
                    timestamp=datetime.datetime.now()
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.add_field(
                    name=f"{author_name} has completed {stats_percentage:.2f}% of total achievements in WARNET",
                    value=f"**{total_completed}**✅ of {len(self.achievement_data)} achievements",
                    inline=False
                )
                embed.add_field(
                    name="Current Badge",
                    value="No Badge" if badge_id == None else f"<@&{badge_id}>",
                    inline=False
                )

                await interaction.followup.send(embed=embed)

    # TODO: If the amount of completed achievement pass a certain amount -> give special role
    @app_commands.command(name='achievement-give', description='Admin or Mod can mark an achievement as complete for specific user')
    async def achievement_give(self, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
        await interaction.response.defer()

        embed: discord.Embed
        member_id = member.id
        author_name = interaction.user.name
        if interaction.user.guild_permissions.administrator:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", member_id)
                if res == None:
                    embed = discord.Embed(
                        color=discord.Colour.red(),
                        title='❌ User not registered',
                        description=f"<@{member_id}> belum terdaftar di database. Silakan <@{member_id}> untuk mendaftar terlebih dahulu menggunakan </achievement-member-register:0>",
                        timestamp=datetime.datetime.now()
                    )

                    await interaction.followup.send(embed=embed)

                else:
                    try:
                        achievement_detail = self.achievement_data[str(achievement_id)]

                    # Handle undefined key
                    except KeyError:
                        error_embed = discord.Embed(
                            color=discord.Colour.red(),
                            title='❌ Achievement not found',
                            description='Cobalah untuk memeriksa apakah id yang diinput sudah benar. Ketik </achievement-list:0> untuk melihat daftar achievement yang tersedia.',
                            timestamp=datetime.datetime.now(),
                        )
                        await interaction.followup.send(embed=error_embed)
                        return

                    try:
                        await conn.execute("INSERT INTO achievement_progress(discord_id, achievement_id) VALUES ($1, $2);", member_id, achievement_id)
                    
                    # Handle duplicate entries
                    except UniqueViolationError:
                        error_embed = discord.Embed(
                            color=discord.Colour.red(),
                            title='❌ Achievement has been added before',
                            description=f'Achievement dengan id `{achievement_id}` sudah ditambahkan sebelumnya pada user <@{member_id}>.',
                            timestamp=datetime.datetime.now(),
                        )
                        await interaction.followup.send(embed=error_embed)
                        return

                    embed = discord.Embed(
                        color=discord.Colour.green(),
                        title='✅ Achievement has been given',
                        description=f"Sukses menambahkan progress achievement kepada <@{member_id}>.",
                        timestamp=datetime.datetime.now()
                    )
                    embed.add_field(name=f"🏅**{achievement_detail['name']}**", value=f"> {achievement_detail['desc']}")
                    embed.set_footer(text=f"Given by {author_name}")

                    await interaction.followup.send(embed=embed)

        else:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title="❌ You don't have permission",
                description=f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini. Cobalah untuk mengontak mereka apabila ingin melakukan claim achievement.",
                timestamp=datetime.datetime.now(),
            )

            await interaction.followup.send(embed=embed)
    
    # TODO: If the amount of completed achievement is below a certain amount -> remove special role
    @app_commands.command(name='achievement-revoke', description='Admin or Mod can mark an achievement as incomplete')
    async def achievement_revoke(self, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
        await interaction.response.defer()

        embed: discord.Embed
        member_id = member.id
        author_name = interaction.user.name        
        if interaction.user.guild_permissions.administrator:
            async with self.db_pool.acquire() as conn:
                res = await conn.fetchval("SELECT discord_id FROM warnet_user WHERE discord_id = $1;", member_id)
                if res == None:
                    embed = discord.Embed(
                        color=discord.Colour.red(),
                        title='❌ User not registered',
                        description=f"<@{member_id}> belum terdaftar di database. Silakan <@{member_id}> untuk mendaftar terlebih dahulu menggunakan </achievement-member-register:0>",
                        timestamp=datetime.datetime.now()
                    )

                    await interaction.followup.send(embed=embed)

                else:
                    try:
                        achievement_detail = self.achievement_data[str(achievement_id)]

                    # Handle undefined key
                    except KeyError:
                        error_embed = discord.Embed(
                            color=discord.Colour.red(),
                            title='❌ Achievement not found',
                            description='Cobalah untuk memeriksa apakah id yang diinput sudah benar. Ketik </achievement-list:0> untuk melihat daftar achievement yang tersedia.',
                            timestamp=datetime.datetime.now(),
                        )
                        await interaction.followup.send(embed=error_embed)
                        return

                    res = await conn.execute("DELETE FROM achievement_progress WHERE discord_id = $1 AND achievement_id = $2;", member_id, achievement_id)
                    if res != 'DELETE 0':
                        embed = discord.Embed(
                            color=discord.Colour.yellow(),
                            title='🗑️ Achievement has been revoked',
                            description=f"Sukses menghapus satu progress achievement milik <@{member_id}>.",
                            timestamp=datetime.datetime.now()
                        )
                        embed.add_field(name=f"~~🏅**{achievement_detail['name']}**~~", value=f"> ~~{achievement_detail['desc']}~~")
                        embed.set_footer(text=f"Revoked by {author_name}")

                        await interaction.followup.send(embed=embed)

                    else:
                        error_embed = discord.Embed(
                            color=discord.Colour.red(),
                            title='❌ Can not revoke the achievement',
                            description=f'User <@{member_id}> tidak pernah mengklaim achievement ini sehingga tidak bisa dilakukan pencabutan.',
                            timestamp=datetime.datetime.now(),
                        )
                        await interaction.followup.send(embed=error_embed)
                        return

        else:
            embed = discord.Embed(
                color=discord.Colour.red(),
                title="❌ You don't have permission",
                description=f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini. Cobalah untuk mengontak mereka apabila ingin melakukan claim achievement.",
                timestamp=datetime.datetime.now(),
            )

            await interaction.followup.send(embed=embed)

    @staticmethod
    def get_achievement_json_data() -> Dict[str, Dict[str, str]]:
        with open(ACHIEVEMENT_DATA_PATH, 'r') as f:
            data = json.load(f)
        
        return data['data']

    @staticmethod
    def get_achievement_badge_id(total_achievement: int) -> Optional[int]:
        """
        return achievement role id based on total completed achievement
        """

        if total_achievement < 10:
            return None
        elif total_achievement < 20:
            return config.ACHIEVEMENT_RANK_ROLE_ID[0]
        elif total_achievement < 50:
            return config.ACHIEVEMENT_RANK_ROLE_ID[1]
        elif total_achievement < 80:
            return config.ACHIEVEMENT_RANK_ROLE_ID[2]
        elif total_achievement < 150:
            return config.ACHIEVEMENT_RANK_ROLE_ID[3]
        else:
            return config.ACHIEVEMENT_RANK_ROLE_ID[4]


    def prepare_achievement_embeds(self) -> List[Embed]:
        total_data = self._total_achievement_data
        total_pages = total_data//10 + 1 if total_data % 10 else total_data//10

        embeds = []
        for page in range(total_pages):
            embed = discord.Embed(
                color=0xfcba03,
                title='WARNET Achievement List',
                description='Berikut daftar achievement yang tersedia di server ini:',
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text='Gunakan command /achievement-detail untuk melihat detail achievement')

            id_start = 10*page + 1
            id_end = 10*(page+1)
            for achievement_id in range(id_start, id_end+1):
                data = self.achievement_data[str(achievement_id)]
                embed.add_field(name=f"🏅`{achievement_id}` {data['name']}", value=f"```{data['desc']}```", inline=False)

            embeds.append(embed)
        
        return embeds


async def setup(bot: WarnetBot) -> None:
    await bot.add_cog(Achievement(bot))