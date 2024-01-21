import datetime
from dataclasses import dataclass


@dataclass
class UserProfile:
    avatar_hash: str
    avatar_url: str
    credits: int
    discriminator: str
    user_id: int
    info_box: str
    reputation: int
    subscription_type: int
    subscription_renewal: datetime.datetime
    title: str
    tokens: int
    username: str
    xp: int
    original: dict


@dataclass
class RankingObject:
    rank: int
    score: int
    user_id: int
    original: dict
    guild_id: int


@dataclass
class GuildRankings:
    guild_id: int
    rankings: list[RankingObject]
    original: dict


@dataclass
class GuildScoreObject:
    guild_id: int
    score: int
    user_id: int
