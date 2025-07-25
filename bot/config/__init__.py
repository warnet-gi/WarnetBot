import os

from dotenv import load_dotenv

load_dotenv()

BOT_DEBUG = int(os.getenv("BOT_DEBUG"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV_BOT_TOKEN = os.getenv("DEV_BOT_TOKEN")

TATSU_TOKEN = os.getenv("TATSU_API_KEY")

GUILD_ID = int(os.getenv("GUILD_ID"))
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID"))

LOCAL_DB_HOST = os.getenv("LOCAL_DB_HOST")
LOCAL_DB_NAME = os.getenv("LOCAL_DB_NAME")
LOCAL_DB_USERNAME = os.getenv("LOCAL_DB_USERNAME")
LOCAL_DB_PASSWORD = os.getenv("LOCAL_DB_PASSWORD")
LOCAL_DB_PORT = int(os.getenv("LOCAL_DB_PORT"))

HOSTED_DB_URI = os.getenv("HOSTED_DB_URI")
HOSTED_DB_HOST = os.getenv("HOSTED_DB_HOST")
HOSTED_DB_NAME = os.getenv("HOSTED_DB_NAME")
HOSTED_DB_USERNAME = os.getenv("HOSTED_DB_USERNAME")
HOSTED_DB_PASSWORD = os.getenv("HOSTED_DB_PASSWORD")
HOSTED_DB_PORT = int(os.getenv("HOSTED_DB_PORT"))

BOT_PREFIX = ['war!', 'War!', 'WAR!']

# These are administrator role on Warnet guild
ADMINISTRATOR_ROLE_ID = {'admin': '761650159833841674', 'mod': '761662280541798421'}
NON_ADMINISTRATOR_ROLE_ID = {'staff': '951170972671701063'}
BOOSTER_ROLE_ID = 768874803712753727
BLACKLIST_GA_ROLE_ID = 944559967191576636

ANNOUNCEMENT_CHANNEL_ID = 761680720245686313
ADMIN_CHANNEL_ID = 761684443915485184
WARN_LOG_CHANNEL_ID = 1058433863333978172
MESSAGE_LOG_CHANNEL_ID = 761684504673910784
TATSU_LOG_CHANNEL_ID = 877432699214782464

BOOSTER_MONTHLY_EXP = 6000


class CustomRoleConfig:
    UPPER_BOUNDARY_ROLE_ID = 975844681634185246
    BOTTOM_BOUNDARY_ROLE_ID = 975845512370606201
    CUSTOM_ROLE_LIMIT = 75

    FONT_NOTO = 'bot/assets/font/NotoSans-Black.ttf'
    FONT_NOTO_JP = 'bot/assets/font/NotoSansJP-Bold.ttf'
    FONT_NOTO_CN = 'bot/assets/font/NotoSansTC-Bold.ttf'
    FONT_SIZE = 30

    BOOSTER_ROLE_ID = 768874803712753727
    BOOSTER_LOG_CHANNEL_ID = 1008600026337005569


class TCGConfig:
    TCG_TITLE_ROLE_ID = (
        1051867676202512415,  # Novice Duelist
        1051865453208801361,  # Expert Duelist
        1051865448980942948,  # Master Duelist
        1051865444073611365,  # Immortal Duelist
    )
    TCG_EVENT_STAFF_ROLE_ID = 977488765234855986
    TCG_MATCH_REPORT_CHANNEL_ID = 1053525411725836428
    TCG_MATCH_LOG_CHANNEL_ID = 1053525862982631516
    TCG_TITLE_EMOJI = {
        TCG_TITLE_ROLE_ID[0]: '<:NoviceDuelist:1052440393461022760>',
        TCG_TITLE_ROLE_ID[1]: '<:ExpertDuelist:1052440396489314304>',
        TCG_TITLE_ROLE_ID[2]: '<:MasterDuelist:1052440400822018078>',
        TCG_TITLE_ROLE_ID[3]: '<:ImmortalDuelist:1052440404135518228>',
    }
