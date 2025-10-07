import asyncio
import logging

from bot import config
from bot.bot import WarnetBot
from bot.config.logger import setup_logger

logging.getLogger("hoyolabrssfeeds").setLevel(logging.ERROR)


def main() -> None:
    bot = WarnetBot()
    try:
        token = config.BOT_TOKEN if not config.BOT_DEBUG else config.DEV_BOT_TOKEN
        if config.BOT_DEBUG:
            bot.debug = True
        asyncio.run(bot.start(debug=bot.debug, token=token))
    except KeyboardInterrupt:
        print("Logging Out...")


if __name__ == "__main__":
    setup_logger()
    main()
