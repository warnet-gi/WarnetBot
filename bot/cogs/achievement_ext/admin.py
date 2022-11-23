import datetime
from asyncpg.exceptions import UniqueViolationError

import discord
from discord import Interaction
from discord.ext import commands

from bot.config import config


async def give_achievement(self: commands.Cog, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
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

                followup_msg = await interaction.followup.send(embed=embed)

                total_completed = await conn.fetchval("SELECT COUNT(*) FROM achievement_progress WHERE discord_id = $1;", member_id)
                role_badge_id, prev_role_badge_id = self.get_achievement_badge_id(total_completed) 
                target_role = None if role_badge_id == None else interaction.guild.get_role(role_badge_id)
                previous_role = None if prev_role_badge_id == None else interaction.guild.get_role(prev_role_badge_id)

                if target_role == None:
                    return

                # Check if the user already has the role or not
                if member.get_role(role_badge_id) == None:
                    try:
                        # give the current role and remove previous role then notify them
                        await member.add_roles(target_role, reason="Completed WARNET achievement level")
                        if previous_role != None:
                            await member.remove_roles(previous_role)

                        notify_embed = discord.Embed(
                            color=target_role.color,
                            description=f"⭐ Selamat {member.mention} telah mendapatkan badge role {target_role.mention} 🎊",
                            timestamp=datetime.datetime.now()
                        )
                        await interaction.channel.send(
                            content=f"{member.mention}",
                            embed=notify_embed,
                            reference=followup_msg
                        )
                    except discord.Forbidden:
                        await interaction.channel.send(content="❌ Bot tidak memiliki izin untuk menambahkan role", reference=followup_msg)
                    except discord.HTTPException:
                        await interaction.channel.send(content="Failed to add the role", reference=followup_msg)


    else:
        await _send_missing_permission_error_embed(interaction)

async def revoke_achievement(self: commands.Cog, interaction: Interaction, member: discord.Member, achievement_id: int) -> None:
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
        await _send_missing_permission_error_embed(interaction)

async def _send_missing_permission_error_embed(interaction: Interaction) -> None:
    embed = discord.Embed(
        color=discord.Colour.red(),
        title="❌ You don't have permission",
        description=f"Hanya <@&{config.ADMINISTRATOR_ROLE_ID['admin']}> atau <@&{config.ADMINISTRATOR_ROLE_ID['mod']}> yang bisa menggunakan command ini. Cobalah untuk mengontak mereka apabila ingin melakukan claim achievement.",
        timestamp=datetime.datetime.now(),
    )

    await interaction.followup.send(embed=embed)