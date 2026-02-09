from __future__ import annotations

import random
from typing import Optional

from .ai_player import AIPlayer
from .game_logic import GameState, Phase, PlayerColor, apply_place, apply_slide, legal_slide_squares


def _legal_place_targets(state: GameState) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for sq in range(9):
        if sq == state.holeSquareIndex:
            continue
        for sl in range(4):
            if state.board[sq][sl] is None:
                out.append((sq, sl))
    return out


def _ai_take_turn_random(state: GameState, *, rng: Optional[random.Random] = None) -> None:
    """
    Random AI:
    - In placement: place randomly, then slide randomly.
    - In movement: slide randomly.
    """
    if state.winner is not None or state.drawReason is not None:
        return
    if state.currentPlayer != PlayerColor.B:
        return

    rng = rng or random.Random()

    if state.phase == Phase.placement:
        targets = _legal_place_targets(state)
        if not targets:
            # Shouldn't happen, but don't crash.
            return
        sq, sl = rng.choice(targets)
        apply_place(state, squareIndex=sq, slotIndex=sl, player=PlayerColor.B)

    # After placement (or in movement), AI must slide if it's still its turn.
    if state.currentPlayer != PlayerColor.B:
        return

    if state.phase in (Phase.placementSlide, Phase.movement):
        slides = legal_slide_squares(state)
        if not slides:
            return
        sq = rng.choice(slides)
        apply_slide(state, squareIndex=sq, player=PlayerColor.B)


_ai_player = AIPlayer.default()


def _ai_take_turn_model(state: GameState, *, rng: Optional[random.Random] = None) -> None:
    """
    ML-driven policy using a TensorFlow model.
    Falls back to random if a trained model is unavailable.
    """
    used_model = _ai_player.take_turn(state, rng=rng)
    if not used_model:
        _ai_take_turn_random(state, rng=rng)


def ai_take_turn(state: GameState, *, mode: str = "random", rng: Optional[random.Random] = None) -> None:
    if mode == "ai":
        _ai_take_turn_model(state, rng=rng)
    else:
        _ai_take_turn_random(state, rng=rng)

