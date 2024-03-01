import datetime
import logging

import aiohttp
from ratelimit import limits

import bot.module.tatsu.data_structures as ds

logger = logging.getLogger(__name__)


class ApiWrapper:
    def __init__(self, key):
        """Initiate the handling request
        :param key: Tatsu API Key. Use 't!apikey create' to obtain this.
        """
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
        """Directly interact with the API to patch object."""
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
        except ValueError:
            subscription_renewal = None

        user = ds.UserProfile(
            avatar_hash=result.get('avatar_hash'),
            avatar_url=result.get('avatar_url'),
            credits_=result.get('credits'),
            discriminator=result.get('discriminator'),
            user_id=result.get('id'),
            info_box=result.get('info_box'),
            reputation=result.get('reputation'),
            subscription_type=result.get('subscription_type'),
            subscription_renewal=subscription_renewal,
            title=result.get('title'),
            tokens=result.get('tokens'),
            username=result.get('username'),
            xp=result.get('xp'),
            original=result,
        )
        return user

    async def get_member_ranking(self, guild_id: int, user_id: int) -> ds.RankingObject:
        """Gets the all-time ranking for a guild member. Returns a guild member ranking object on success.
        :param guild_id: The ID of the guild
        :param user_id: The user id
        guild member ranking object: guild_id, rank, score, user_id, and dict all of that
        """
        try:
            result = await self.request(f"/guilds/{guild_id}/rankings/members/{user_id}/all")
        except Exception as e:
            raise e
        rank = self.ranking_object(result)
        return rank

    @staticmethod
    def ranking_object(result) -> ds.RankingObject:
        """Initiate the rank profile.
        Returns guild_id, rank, score, user_id, and dict all of that"""
        rank = ds.RankingObject(
            guild_id=result.get('guild_id'),
            rank=result.get('rank'),
            score=result.get('score'),
            user_id=result.get('user_id'),
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
            guild_id=result.get('guild_id'),
            rankings=[self.ranking_object(i) for i in result.get('rankings', [{}])],
            original=result,
        )
        return rankings

    async def _modify_score(
        self, action_type: int, guild_id: int, user_id: int, amount: int
    ) -> ds.GuildScoreObject:
        url = f"/guilds/{guild_id}/members/{user_id}/score"
        payload = {'action': action_type, 'amount': amount}

        result = await self.patch(url, payload)

        score = ds.GuildScoreObject(
            guild_id=result.get('guild_id'),
            score=result.get('score'),
            user_id=result.get('user_id'),
        )
        return score

    async def add_score(self, guild_id: int, user_id: int, amount: int) -> ds.GuildScoreObject:
        return await self._modify_score(0, guild_id, user_id, amount)

    async def remove_score(self, guild_id: int, user_id: int, amount: int) -> ds.GuildScoreObject:
        return await self._modify_score(1, guild_id, user_id, amount)
