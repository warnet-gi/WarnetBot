import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from anyio import open_file

from bot.config.news import JSON_GENSHIN_NEWS_PATH


@dataclass
class GenshinNewsListElement:
    s_chan_id: list[int]
    s_title: str
    s_intro: str
    s_url: str
    s_author: str
    s_content: str
    s_ext: str
    dt_start_time: datetime
    dt_end_time: datetime
    dt_create_time: datetime
    i_info_id: int
    s_tag_name: list[Any]
    s_category_name: str


@dataclass
class GenshinNewsData:
    i_total: int
    list: list[GenshinNewsListElement]


@dataclass
class GenshinNews:
    retcode: int
    message: str
    data: GenshinNewsData


async def get_genshin_news(number: int = 10) -> None:
    url = (
        "https://api-os-takumi-static.hoyoverse.com/content_v2_user/app/"
        "a1b1f9d3315447cc/getContentList"
        f"?iAppId=32&iChanId=395&iPageSize={number}&iPage=1&sLangKey=id-id"
    )
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()

    json_path = Path(JSON_GENSHIN_NEWS_PATH)
    json_path.mkdir(parents=True, exist_ok=True)
    async with await open_file(JSON_GENSHIN_NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
