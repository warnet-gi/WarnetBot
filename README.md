<p align="center">
    <img src="https://user-images.githubusercontent.com/20255031/214029670-2d0495f5-4a00-40aa-8452-57324644486e.png" width="50%" style="text-align:center"/>
</p>

<h1 align="center">Warnet Bot</h1>
<p align="center">
    A bot for Warga Nusantara Teyvat a.k.a WARNET (<a href="https://discord.gg/warnet-gi">https://discord.gg/warnet-gi</a>).
</p>

<p align="center">
    <img src="https://discordapp.com/api/guilds/761644411486339073/widget.png?style=banner2" width="50%" style="text-align:center"/>
</p>

<p align="center">
    <img src="https://github.com/Iqrar99/WarnetBot/assets/20255031/538a816b-91de-4023-bd13-871dd4eafd66" width="50%" style="text-align:center"/>
</p>

---

## Requirement
- python 3.10
- postgresql

## How to contribute?
1. Fork or clone the project
2. Create a [New Application](https://discord.com/developers/applications).
3. Create a bot by going to Bot -> Add Bot -> Yes, do it!
4. Copy the bot token and paste it into the `BOT_TOKEN` environment variable (see the next step).
5. Rename `.env.example` to `.env` and edit `.env` to your bot.
6. Create python virtual environment by using `python -m venv env`.
7. Enter the virtual environment by using command `source env/Scripts/Activate` (Linux) or `env\Scripts\Activate.bat` (Windows)
8. Make sure you have installed `poetry`. Install it using `pip install poetry` on your virtual environment.
9. Install the depedencies using `poetry install`.
10. Execute the database creation script from `bot\data\db.sql` on your database console.
11. Set `BOT_DEBUG=true` to run the bot in debug mode on `.env`. Set to `false` only for production.
12. To start the bot, use `poetry run task start`.

## Usage Guide
To learn how to use this bot, please visit our [wiki documentation](https://github.com/Iqrar99/WarnetBot/wiki) for the commands info.

## License
The Warnet Bot is open-sourced software licensed under the [MIT License](https://opensource.org/licenses/MIT).
