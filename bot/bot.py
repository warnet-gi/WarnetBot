import logging
import time
from pathlib import Path

import aiohttp
import asyncpg
import discord
from discord.ext.commands import Bot

import bot.module.tatsu.data_structures as ds
from bot import __version__, config
from bot.module.tatsu.wrapper import ApiWrapper

logger = logging.getLogger(__name__)
BOT_PREFIX = config.BOT_PREFIX


class WarnetBot(Bot):
    debug: bool
    bot_app_info: discord.AppInfo
    db_pool: asyncpg.Pool

    def __init__(self) -> None:
        super().__init__(
            command_prefix=BOT_PREFIX,
            strip_after_prefix=True,
            intents=discord.Intents.all(),
            help_command=None,
            log_handler=None,
        )
        self.session: aiohttp.ClientSession = None
        self.version = __version__

    async def on_ready(self) -> None:
        print("The bot is online!")
        print(f"Logged in as {self.user}")
        print("------------------")

    async def setup_hook(self) -> None:
        if not self.session:
            self.session = aiohttp.ClientSession()

        self.bot_app_info = await self.application_info()
        if self.bot_app_info.team is not None:
            self.owner_ids = {m.id for m in self.bot_app_info.team.members}
        else:
            self.owner_ids = {self.bot_app_info.owner.id}

        await self.load_cogs()

    async def load_cogs(self) -> None:
        cogs_path = Path("./bot/cogs")
        for file in cogs_path.iterdir():
            if file.is_file() and file.suffix == ".py" and file.name != "__init__.py":
                await self.load_extension(f"bot.cogs.{file.stem}")

        logger.info("ALL COGS HAVE BEEN LOADED SUCCESSFULLY")

    async def close(self) -> None:
        await self.session.close()
        await super().close()

    async def start(
        self, token: str, *, reconnect: bool = True, debug: bool = False
    ) -> None:
        self.start_time = time.time()
        self.debug = debug

        if self.debug:
            logger.debug("Running in debug mode")

            db_pool = await asyncpg.create_pool(
                host=config.LOCAL_DB_HOST,
                user=config.LOCAL_DB_USERNAME,
                database=config.LOCAL_DB_NAME,
                password=config.LOCAL_DB_PASSWORD,
                port=config.LOCAL_DB_PORT,
            )
            if db_pool is None:
                err = "Database pool is none"
                raise ValueError(err)
            self.db_pool = db_pool

        else:
            db_pool = await asyncpg.create_pool(dsn=config.HOSTED_DB_URI)
            if db_pool is None:
                err = "Database pool is none"
                raise ValueError(err)
            self.db_pool = db_pool

        return await super().start(token, reconnect=reconnect)

    def get_db_pool(self) -> asyncpg.Pool:
        return self.db_pool


class TatsuApi:
    API = ApiWrapper(config.TATSU_TOKEN)

    async def add_score(self, member_id: int, amount: int) -> ds.GuildScoreObject:
        return await self.API.add_score(config.GUILD_ID, member_id, amount)
