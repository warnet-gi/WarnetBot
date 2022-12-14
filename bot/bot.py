import os
import aiohttp
import logging
import asyncpg
import time

import discord
from discord.ext import commands

from dotenv import load_dotenv
from bot.config import config

load_dotenv()

discord.utils.setup_logging(level=logging.INFO, root=False)

BOT_PREFIX = config.DEFAULT['prefix']
PRIVATE_DEV_GUILD_ID = config.PRIVATE_DEV_GUILD_ID
WARNET_GUILD_ID = config.WARNET_GUILD_ID

class WarnetBot(commands.Bot):
    debug: bool    
    bot_app_info: discord.AppInfo
    db_pool: asyncpg.Pool

    def __init__(self) -> None:
        super().__init__(command_prefix=BOT_PREFIX, strip_after_prefix=True, intents=discord.Intents.all(), help_command=None)
        self.session: aiohttp.ClientSession = None
        # self.synced = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("The bot is online!")
        print("Logged in as {}".format(self.user))
        print("------------------")

        self.start_time = time.time()

        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name='Pengguna WARNET')
        )

    async def setup_hook(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            self.owner_id = config.OWNER_ID
        except ValueError:
            self.bot_app_info = await self.application_info()
            self.owner_id = self.bot_app_info.owner.id
            
        await self.load_cogs()
        
        # This copies the global commands over to your guild.
        development_guild = discord.Object(PRIVATE_DEV_GUILD_ID)
        if development_guild:
            self.tree.copy_global_to(guild=development_guild)
            synced = await self.tree.sync(guild=development_guild)
        else:
            synced = await self.tree.sync()
        
        print("Synced {} command(s)".format(len(synced)))

    async def load_cogs(self) -> None:
        for filename in os.listdir('./bot/cogs'):
            if filename.endswith('.py'):
                await self.load_extension('bot.cogs.{}'.format(filename[:-3]))

    async def close(self) -> None:
        await self.session.close()
        await super().close()

    async def start(self, debug: bool = False) -> None:
        self.debug = debug
        self.db_pool = await asyncpg.create_pool(
            host=os.getenv('LOCAL_DB_HOST'),
            user=os.getenv('LOCAL_DB_USERNAME'),
            database=os.getenv('LOCAL_DB_NAME'),
            password=os.getenv('LOCAL_DB_PASSWORD'),
            port=os.getenv('LOCAL_DB_PORT')
        )
        return await super().start(os.getenv('BOT_TOKEN'), reconnect=True)

    def get_db_pool(self) -> asyncpg.Pool:
        return self.db_pool
