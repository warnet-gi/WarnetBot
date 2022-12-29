import os
import aiohttp
import logging
import asyncpg
import time

import discord
from discord.ext.commands import Bot

from dotenv import load_dotenv
from bot.config import config

load_dotenv()

discord.utils.setup_logging(level=logging.INFO, root=False)

BOT_PREFIX = config.DEFAULT['prefix']
PRIVATE_DEV_GUILD_ID = config.PRIVATE_DEV_GUILD_ID
WARNET_GUILD_ID = config.WARNET_GUILD_ID

class WarnetBot(Bot):
    debug: bool    
    bot_app_info: discord.AppInfo
    db_pool: asyncpg.Pool

    def __init__(self) -> None:
        super().__init__(command_prefix=BOT_PREFIX, strip_after_prefix=True, intents=discord.Intents.all(), help_command=None)
        self.session: aiohttp.ClientSession = None

    async def on_ready(self) -> None:
        print("The bot is online!")
        print("Logged in as {}".format(self.user))
        print("------------------")

    async def setup_hook(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            self.owner_id = config.OWNER_ID
        except ValueError:
            self.bot_app_info = await self.application_info()
            self.owner_id = self.bot_app_info.owner.id
            
        await self.load_cogs()
        
    async def load_cogs(self) -> None:
        for filename in os.listdir('./bot/cogs'):
            if filename.endswith('.py'):
                await self.load_extension('bot.cogs.{}'.format(filename[:-3]))

    async def close(self) -> None:
        await self.session.close()
        await super().close()

    async def start(self, debug: bool = False) -> None:
        self.start_time = time.time()
        self.debug = debug

        if self.debug:
            self.db_pool = await asyncpg.create_pool(
                host=os.getenv('LOCAL_DB_HOST'),
                user=os.getenv('LOCAL_DB_USERNAME'),
                database=os.getenv('LOCAL_DB_NAME'),
                password=os.getenv('LOCAL_DB_PASSWORD'),
                port=os.getenv('LOCAL_DB_PORT')
            )

            return await super().start(os.getenv('DEVELOPMENT_BOT_TOKEN'), reconnect=True)
        
        else:
            self.db_pool = await asyncpg.create_pool(
                host=os.getenv('HOSTED_DB_HOST'),
                user=os.getenv('HOSTED_DB_USERNAME'),
                database=os.getenv('HOSTED_DB_NAME'),
                password=os.getenv('HOSTED_DB_PASSWORD'),
                port=os.getenv('HOSTED_DB_PORT')
            )

            return await super().start(os.getenv('BOT_TOKEN'), reconnect=True)

    def get_db_pool(self) -> asyncpg.Pool:
        return self.db_pool
