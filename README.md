<p align="center">
    <img src="https://user-images.githubusercontent.com/20255031/214029670-2d0495f5-4a00-40aa-8452-57324644486e.png" width="50%" style="text-align:center"/>
</p>

<h1 align="center">Warnet Bot</h1>
<p align="center">
    A bot for Warga Nusantara Teyvat a.k.a WARNET (<a href="https://discord.gg/warnet-gi">https://discord.gg/warnet-gi</a>).
</p>

<p align="center">
    <img src="https://user-images.githubusercontent.com/20255031/214031213-a4be0c93-3e01-4d80-a9bf-5927f632bf82.png" width="50%" style="text-align:center"/>
</p>

---

## How to contribute?
1. Clone the project
2. Create a [New Application](https://discord.com/developers/applications).
3. Create a bot by going to Bot -> Add Bot -> Yes, do it!
4. Copy the bot token and paste it into the `DEVELOPMENT_BOT_TOKEN` environment variable (see the next step).
5. Create `.env` file. It should contain these variables:
    ```bash
    DEVELOPMENT_BOT_TOKEN="YOUR_BOT_TOKEN"  
    BOT_TOKEN="YOUR_BOT_TOKEN"  # Variable when debug = False

    LOCAL_DB_URI="YOUR_LOCAL_DB_URI"
    LOCAL_DB_HOST="localhost"
    LOCAL_DB_NAME="YOUR_LOCAL_DB_NAME"
    LOCAL_DB_PORT="YOUR_LOCAL_DB_PORT"
    LOCAL_DB_USERNAME="YOUR_LOCAL_DB_USERNAME"
    LOCAL_DB_PASSWORD="YOUR_LOCAL_DB_PASSWORD"

    # Use these env variables only if you want to
    # test your hosted database when debug = False
    HOSTED_DB_URI="YOUR_HOSTED_DB_URI"
    HOSTED_DB_HOST="YOUR_DB_HOST"
    HOSTED_DB_NAME="YOUR_HOSTED_DB_NAME"
    HOSTED_DB_PORT="YOUR_HOSTED_DB_PORT"
    HOSTED_DB_USERNAME="YOUR_HOSTED_DB_USERNAME"
    HOSTED_DB_PASSWORD="YOUR_HOSTED_DB_PASSWORD"
    ```
6. Create python virtual environment by using `python -m venv env`.
7. Enter the virtual environment by using command `source env/Scripts/Activate` (Linux) or `env\Scripts\Activate.bat` (Windows)
8. Make sure you have installed `poetry`. Install it using `pip install poetry` on your virtual environment.
9. Install the depedencies using `poetry install`.
10. Make sure to install postgreSQL on local machine and execute the database creation script on `bot\data\db.sql`.
11. Change the `OWNER_ID` on config file `bot\config\config.py` with your own id for testing.
12. Set `debug=True` to run the bot in debug mode on `bot\__main__.py`.
13. To start the bot, use `poetry run task start`.

## Usage Guide
To learn how to use this bot, please visit our [wiki documentation](https://github.com/Iqrar99/WarnetBot/wiki) for the commands info.