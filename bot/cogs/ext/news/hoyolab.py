from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TypedDict

import hoyolabrssfeeds as hrf

from bot.config.news import JSON_HOYOLAB_NEWS_PATH


def hoyolab_news() -> hrf.GameFeed:
    genshin_meta = hrf.models.FeedMeta(
        game=hrf.models.Game.GENSHIN,
        language=hrf.models.Language.INDONESIAN,
    )
    json_path = Path(JSON_HOYOLAB_NEWS_PATH)
    json_writer_config = hrf.models.FeedFileWriterConfig(
        feed_type=hrf.models.FeedType.JSON,
        path=json_path,
    )
    json_writer = hrf.writers.JSONFeedFileWriter(config=json_writer_config)

    return hrf.feeds.GameFeed(
        feed_meta=genshin_meta,
        feed_writers=[json_writer],
    )


class Name(Enum):
    GI_OFFICIAL_ID = "GI Official - ID"
    HILICHURL_YANG_GIAT = "Hilichurl yang Giat"


@dataclass
class HoyolabNewsAuthor(TypedDict):
    name: Name


class HoyolabNewsTag(Enum):
    EVENTS = "Events"
    INFO = "Info"
    NOTICES = "Notices"


@dataclass
class HoyolabNewsItem(TypedDict):
    id: int
    url: str
    title: str
    authors: list[HoyolabNewsAuthor]
    tags: list[HoyolabNewsTag]
    content_html: str
    date_published: datetime
    summary: str
    image: str


@dataclass
class HoyolabNews(TypedDict):
    version: str
    title: str
    language: str
    home_page_url: str
    items: list[HoyolabNewsItem]
