# OP Warnet Bot
A bot for Warga Nusantara Teyvat (WARNET) [discord server](https://discord.gg/warnet-gi)

---
## How to contribute?
1. Clone the project
2. Create python virtual env by using `python -m venv env`. Enter the virtual environment by using command `source env/Scripts/Activate` (Linux) or `env\Scripts\Activate.bat` (Windows)
3. Make sure you have installed `poetry`
4. Install the depedencies using `poetry install`
5. Create `.env` file. It should contain these variables:
    ```bash
    BOT_TOKEN="YOUR_BOT_TOKEN"
    BOT_INVITE_LINK="YOUR_BOT_INVITE_LINK"
    OWNER_ID="DISCORD_BOT_OWNER_ID"
    ```
6. To run the bot, use `poetry run task start`