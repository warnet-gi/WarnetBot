import json
import os

import aiohttp

from bot.config.news import JSON_GENSHIN_NEWS_PATH


async def get_genshin_news(number: int = 10) -> None:
    url = (
        "https://api-os-takumi-static.hoyoverse.com/content_v2_user/app/"
        "a1b1f9d3315447cc/getContentList"
        f"?iAppId=32&iChanId=395&iPageSize={number}&iPage=1&sLangKey=id-id"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()

    os.makedirs(os.path.dirname(JSON_GENSHIN_NEWS_PATH), exist_ok=True)
    with open(JSON_GENSHIN_NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
