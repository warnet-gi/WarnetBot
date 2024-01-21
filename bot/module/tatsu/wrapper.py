import datetime

import aiohttp
from ratelimit import limits

import bot.module.tatsu.data_structures as ds


class ApiWrapper:
    def __init__(self, key):
        self.key = key
        self.base_url = "https://api.tatsu.gg/v1/"
        self.headers = {"Authorization": key}

    @limits(calls=60, period=60)
    async def request(self, url):
        """Directly interact with the API to get the unfiltered results."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.base_url + url, headers=self.headers) as result:
                if result.status != 200:
                    return result.raise_for_status()
                return await result.json()

    @limits(calls=60, period=60)
    async def patch(self, url, payload):
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url=self.base_url + url, json=payload, headers=self.headers
            ) as result:
                if result.status != 200:
                    return result.raise_for_status()
                return await result.json()

    async def get_profile(self, user_id: int) -> ds.UserProfile:
        """Gets a user's profile. Returns a user object on success."""
        try:
            result = await self.request(f"users/{user_id}/profile")
        except Exception as e:
            raise e
        try:
            subscription_renewal = datetime.datetime.strptime(
                result.get("subscription_renewal"), "%Y-%m-%dT%H:%M:%SZ"
            )
        except Exception:
            subscription_renewal = None
        user = ds.UserProfile(
            avatar_hash=result.get('avatar_hash', None),
            avatar_url=result.get('avatar_url', None),
            credits_=result.get('credits', None),
            discriminator=result.get('discriminator', None),
            user_id=result.get('id', None),
            info_box=result.get('info_box', None),
            reputation=result.get('reputation', None),
            subscription_type=result.get('subscription_type', None),
            subscription_renewal=subscription_renewal,
            title=result.get('title', None),
            tokens=result.get('tokens', None),
            username=result.get('username', None),
            xp=result.get('xp', None),
            original=result,
        )
        return user

    async def get_member_ranking(self, guild_id: int, user_id: int) -> ds.RankingObject:
        """Gets the all-time ranking for a guild member. Returns a guild member ranking object on success.
        :param guild_id: The ID of the guild
        :param user_id: The user id
        """
        try:
            result = await self.request(f"/guilds/{guild_id}/rankings/members/{user_id}/all")
        except Exception as e:
            raise e
        rank = self.ranking_object(result)
        return rank

    @staticmethod
    def ranking_object(result) -> ds.RankingObject:
        """Initiate the rank profile"""
        rank = ds.RankingObject(
            guild_id=result.get('guild_id', None),
            rank=result.get('rank', None),
            score=result.get('score', None),
            user_id=result.get('user_id', None),
            original=result,
        )
        return rank

    async def get_guild_rankings(self, guild_id, timeframe="all", offset=0) -> ds.GuildRankings:
        """Gets all-time rankings for a guild. Returns a guild rankings object on success.
        :param guild_id: The ID of the guild
        :param timeframe: Can be all, month or week
        :param offset: The guild rank offset
        """
        try:
            result = await self.request(f"/guilds/{guild_id}/rankings/{timeframe}?offset={offset}")
        except Exception as e:
            raise e
        rankings = ds.GuildRankings(
            guild_id=result.get('guild_id', None),
            rankings=[self.ranking_object(i) for i in result.get('rankings', [{}])],
            original=result,
        )
        return rankings

    async def add_score(self, guild_id: int, user_id: int, amount: int) -> ds.GuildScoreObject:
        url = f"/guilds/{guild_id}/members/{user_id}/score"
        payload = {'action': 0, 'amount': amount}
        try:
            result = await self.patch(url, payload)
        except Exception as e:
            raise e
        score = ds.GuildScoreObject(
            guild_id=result.get('guild_id', None),
            score=result.get('score', None),
            user_id=result.get('user_id', None),
        )
        return score
