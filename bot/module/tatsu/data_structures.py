import datetime


class UserProfile:
    def __init__(
        self,
        avatar_hash,
        avatar_url,
        credits_,
        discriminator,
        user_id,
        info_box,
        reputation,
        subscription_type,
        subscription_renewal,
        title,
        tokens,
        username,
        xp,
        original,
    ):
        self.avatar_has: str = avatar_hash
        self.avatar_url: str = avatar_url
        self.credits: int = credits_
        self.discriminator: str = discriminator
        self.user_id: int = int(user_id) if user_id else user_id
        self.info_box: str = info_box
        self.reputation: int = reputation
        self.subscription_type: int = subscription_type
        self.subscription_renewal: datetime.datetime = subscription_renewal
        self.title: str = title
        self.tokens: int = tokens
        self.username: str = username
        self.xp: int = xp
        self.original: dict = original


class GuildRankings:
    def __init__(self, guild_id, rankings, original):
        self.guild_id: int = int(guild_id) if guild_id else guild_id
        self.rankings: [RankingObject] = rankings
        self.original: dict = original


class RankingObject:
    def __init__(self, rank, score, user_id, original, guild_id=None):
        self.rank: int = rank
        self.score: int = score
        self.user_id: int = int(user_id) if user_id else user_id
        self.original: dict = original
        self.guild_id: int = int(guild_id) if guild_id else guild_id


class GuildScoreObject:
    def __init__(self, guild_id, score, user_id):
        self.guild_id: int = int(guild_id) if guild_id else guild_id
        self.score: int = score
        self.user_id: int = int(user_id) if user_id else user_id
