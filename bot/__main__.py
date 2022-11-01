import asyncio
from bot.bot import WarnetBot

def main():
    bot = WarnetBot()
    asyncio.run(bot.start())


if __name__ == "__main__":
    main()