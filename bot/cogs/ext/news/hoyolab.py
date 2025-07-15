import hoyolabrssfeeds as hrf

from bot.config.news import JSON_HOYOLAB_NEWS_PATH


def hoyolab_news():
    genshin_meta = hrf.models.FeedMeta(
        game=hrf.models.Game.GENSHIN,
        language=hrf.models.Language.INDONESIAN,
    )
    json_writer_config = hrf.models.FeedFileWriterConfig(
        feed_type=hrf.models.FeedType.JSON,
        path=JSON_HOYOLAB_NEWS_PATH,
    )
    json_writer = hrf.writers.JSONFeedFileWriter(config=json_writer_config)

    genshin_feed = hrf.feeds.GameFeed(
        feed_meta=genshin_meta,
        feed_writers=[json_writer],
    )

    return genshin_feed
