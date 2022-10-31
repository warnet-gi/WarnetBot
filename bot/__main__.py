import os
import aiohttp
import asyncio

import discord
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()

BOT_PREFIX = 'war!'

class WarnetBot(commands.Bot):
    debug: bool    
    bot_app_info: discord.AppInfo

    def __init__(self) -> None:
        super().__init__(command_prefix=BOT_PREFIX, strip_after_prefix=True, intents=discord.Intents.all())
        self.session: aiohttp.ClientSession = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("The bot is online!")
        print("Logged in as {}".format(self.user))
        print("------------------")

        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name='Pengguna WARNET')
        )

    async def setup_hook(self):
        return await super().setup_hook()

    async def load_cogs(self):
        initial_extension = []
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                initial_extension.append('cogs.' + filename[:-3])
        
        await self.load_extension(initial_extension)

    async def close(self):
        await self.session.close()
        await super().close()

    async def start(self, debug: bool = False):
        self.debug = debug
        return await super().start(os.getenv('BOT_TOKEN'), reconnect=True)


def main():
    bot = WarnetBot()
    asyncio.run(bot.start())


if __name__ == "__main__":
    main()