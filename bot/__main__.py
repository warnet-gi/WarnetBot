import asyncio

from bot import config
from bot.bot import WarnetBot


def main():
    bot = WarnetBot()
    try:
        asyncio.run(bot.start(debug=config.BOT_DEBUG))
    except KeyboardInterrupt:
        print("Logging Out...")


if __name__ == "__main__":
    main()
