import os
import aiohttp
import asyncio
import logging

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

discord.utils.setup_logging(level=logging.INFO, root=False)

BOT_PREFIX = 'war!'

class WarnetBot(commands.Bot):
    debug: bool    
    bot_app_info: discord.AppInfo

    def __init__(self) -> None:
        super().__init__(command_prefix=BOT_PREFIX, strip_after_prefix=True, intents=discord.Intents.all(), help_command=None)
        self.session: aiohttp.ClientSession = None

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        synced = await self.tree.sync()
        
        print("Synced {} command(s)".format(len(synced)))
        print("The bot is online!")
        print("Logged in as {}".format(self.user))
        print("------------------")

        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name='Pengguna WARNET')
        )

    async def setup_hook(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            self.owner_id = int(os.getenv('OWNER_ID'))
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
        self.debug = debug
        return await super().start(os.getenv('BOT_TOKEN'), reconnect=True)
