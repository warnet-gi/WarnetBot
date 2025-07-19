import json
from dataclasses import dataclass
from typing import Any, TypedDict

import aiohttp
from anyio import open_file

from bot.config.news import JSON_GENSHIN_NEWS_PATH


async def get_genshin_news(number: int = 10) -> None:
    url = (
        "https://api-os-takumi-static.hoyoverse.com/content_v2_user/app/"
        "a1b1f9d3315447cc/getContentList"
        f"?iAppId=32&iChanId=395&iPageSize={number}&iPage=1&sLangKey=id-id"
    )
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()

    async with await open_file(JSON_GENSHIN_NEWS_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))


@dataclass
class GenshinNewsListElement(TypedDict):
    sChanId: list[int]
    sTitle: str
    sIntro: str
    sUrl: str
    sAuthor: str
    sContent: str
    sExt: str
    dtStartTime: str
    dtEndTime: str
    dtCreateTime: str
    iInfoId: int
    sTagName: list[Any]
    sCategoryName: str


@dataclass
class GenshinNewsData(TypedDict):
    iTotal: int
    list: list[GenshinNewsListElement]


@dataclass
class GenshinNews(TypedDict):
    retcode: int
    message: str
    data: GenshinNewsData


@dataclass
class Banner(TypedDict):
    name: str
    url: str


@dataclass
class GenshinNewsSext(TypedDict):
    banner: list[Banner]
    title: str
