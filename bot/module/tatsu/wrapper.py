from typing import TypeVar, cast

import aiohttp
from ratelimit import limits

import bot.module.tatsu.data_structures as ds

T = TypeVar("T")


class ApiWrapper:
    def __init__(self, key: str) -> None:
        self.key = key
        self.base_url = "https://api.tatsu.gg/v1/"
        self.headers = {"Authorization": key}

    @limits(calls=60, period=60)
    async def _patch(self, url: str, payload: dict, _: type[T]) -> T:
        async with (
            aiohttp.ClientSession() as session,
            session.patch(
                url=self.base_url + url,
                json=payload,
                headers=self.headers,
                raise_for_status=True,
            ) as result,
        ):
            json_result = await result.json()
            return cast("T", json_result)

    async def _modify_score(
        self, action_type: int, guild_id: int, user_id: int, amount: int
    ) -> ds.GuildScoreObject:
        url = f"/guilds/{guild_id}/members/{user_id}/score"
        payload = {"action": action_type, "amount": amount}

        result = await self._patch(
            url,
            payload,
            ds.GuildScoreObject,
        )

        return ds.GuildScoreObject(
            guild_id=result["guild_id"],
            score=result["score"],
            user_id=result["user_id"],
        )

    async def add_score(
        self, guild_id: int, user_id: int, amount: int
    ) -> ds.GuildScoreObject:
        return await self._modify_score(0, guild_id, user_id, amount)

    async def remove_score(
        self, guild_id: int, user_id: int, amount: int
    ) -> ds.GuildScoreObject:
        return await self._modify_score(1, guild_id, user_id, amount)
