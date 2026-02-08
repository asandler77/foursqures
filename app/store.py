from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from .game_logic import GameState, PlayerColor, new_state


@dataclass
class PlayerInfo:
    token: str
    color: PlayerColor


@dataclass
class Game:
    id: str
    state: GameState
    red: PlayerInfo
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class InMemoryStore:
    def __init__(self) -> None:
        self._games: dict[str, Game] = {}

    def create_game(self, *, pieces_per_player: int = 8) -> Game:
        game_id = str(uuid4())
        red_token = str(uuid4())
        state = new_state(pieces_per_player=pieces_per_player)
        g = Game(id=game_id, state=state, red=PlayerInfo(token=red_token, color=PlayerColor.R))
        self._games[game_id] = g
        return g

    def get_game(self, game_id: str) -> Game:
        g = self._games.get(game_id)
        if g is None:
            raise KeyError("game not found")
        return g

    def resolve_player(self, g: Game, token: str) -> PlayerInfo:
        if token == g.red.token:
            return g.red
        raise PermissionError("invalid player token")


store = InMemoryStore()

