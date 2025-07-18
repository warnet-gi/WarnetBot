from dataclasses import dataclass
from typing import TypedDict


@dataclass
class GuildScoreObject(TypedDict):
    guild_id: int
    score: int
    user_id: int
