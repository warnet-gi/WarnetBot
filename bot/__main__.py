import os
import discord
from discord import Intents
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

client = commands.Bot(
    command_prefix='war!',
    intents=Intents.all()
)

@client.event
async def on_ready():
    print("The bot is online!")
    print("------------------")


@client.command()
async def hello(ctx):
    await ctx.send("Hello")


def main():
    client.run(token=os.getenv('BOT_TOKEN'))


if __name__ == "__main__":
    main()