from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

Action = Literal["place", "slide"]


class PlayerColor(str, Enum):
    R = "R"  # human
    B = "B"  # AI


class Phase(str, Enum):
    placement = "placement"
    placementSlide = "placementSlide"
    movement = "movement"


@dataclass
class GameState:
    board: list[list[Optional[str]]]  # 9 arrays of 4: null | "R" | "B"
    phase: Phase
    currentPlayer: PlayerColor
    placed: dict[PlayerColor, int]
    piecesPerPlayer: int
    holeSquareIndex: int
    # New rule: cannot slide the same square that was slid on the previous turn.
    # We store the square index where the last-slid square currently sits (the previous hole index).
    blockedSlideSquareIndex: Optional[int] = None
    winner: Optional[PlayerColor] = None
    drawReason: Optional[str] = None


class IllegalMove(ValueError):
    pass


def new_state(*, pieces_per_player: int = 16) -> GameState:
    if pieces_per_player <= 0:
        raise ValueError("piecesPerPlayer must be positive")

    return GameState(
        board=[[None, None, None, None] for _ in range(9)],
        phase=Phase.placement,
        currentPlayer=PlayerColor.R,
        placed={PlayerColor.R: 0, PlayerColor.B: 0},
        piecesPerPlayer=pieces_per_player,
        holeSquareIndex=4,
        blockedSlideSquareIndex=None,
        winner=None,
        drawReason=None,
    )


def square_row(square_index: int) -> int:
    return square_index // 3


def square_col(square_index: int) -> int:
    return square_index % 3


def slot_row(slot_index: int) -> int:
    return slot_index // 2


def slot_col(slot_index: int) -> int:
    return slot_index % 2


def _assert_square_index(i: int) -> None:
    if not (0 <= i <= 8):
        raise IllegalMove("squareIndex out of bounds")


def _assert_slot_index(i: int) -> None:
    if not (0 <= i <= 3):
        raise IllegalMove("slotIndex out of bounds")


def _global_get(state: GameState, r: int, c: int) -> Optional[str]:
    sq = (r // 2) * 3 + (c // 2)
    sl = (r % 2) * 2 + (c % 2)
    return state.board[sq][sl]


def detect_winner(state: GameState) -> Optional[PlayerColor]:
    # Any 2x2 solid block on global 6x6, including across 4 squares.
    for r in range(5):
        for c in range(5):
            a = _global_get(state, r, c)
            if a is None:
                continue
            b = _global_get(state, r, c + 1)
            d = _global_get(state, r + 1, c)
            e = _global_get(state, r + 1, c + 1)
            if a == b == d == e:
                return PlayerColor(a)
    return None


def legal_slide_squares(state: GameState) -> list[int]:
    """Squares that can slide into the hole (adjacent to hole)."""
    h = state.holeSquareIndex
    hr, hc = square_row(h), square_col(h)
    out: list[int] = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r, c = hr + dr, hc + dc
        if 0 <= r <= 2 and 0 <= c <= 2:
            out.append(r * 3 + c)
    # New rule: disallow sliding the same square as previous slide (prevents immediate backtracking).
    if state.blockedSlideSquareIndex is not None:
        out = [i for i in out if i != state.blockedSlideSquareIndex]
    return out


def _maybe_set_draw_no_slides(state: GameState) -> None:
    if state.phase != Phase.movement:
        return
    if len(legal_slide_squares(state)) == 0:
        state.drawReason = "noLegalSlides"


def apply_place(state: GameState, *, squareIndex: int, slotIndex: int, player: PlayerColor) -> None:
    if state.winner is not None or state.drawReason is not None:
        raise IllegalMove("game already finished")
    if state.phase != Phase.placement:
        raise IllegalMove("cannot place in this phase")
    if player != state.currentPlayer:
        raise IllegalMove("not your turn")

    _assert_square_index(squareIndex)
    _assert_slot_index(slotIndex)
    if squareIndex == state.holeSquareIndex:
        raise IllegalMove("cannot place into the hole square")
    if state.placed[player] >= state.piecesPerPlayer:
        raise IllegalMove("no pieces remaining to place")
    if state.board[squareIndex][slotIndex] is not None:
        raise IllegalMove("slot is occupied")

    state.board[squareIndex][slotIndex] = player.value
    state.placed[player] += 1

    w = detect_winner(state)
    if w is not None:
        state.winner = w
        return

    # After a placement, same player must slide.
    state.phase = Phase.placementSlide


def apply_slide(state: GameState, *, squareIndex: int, player: PlayerColor) -> None:
    if state.winner is not None or state.drawReason is not None:
        raise IllegalMove("game already finished")
    if state.phase not in (Phase.placementSlide, Phase.movement):
        raise IllegalMove("cannot slide in this phase")
    if player != state.currentPlayer:
        raise IllegalMove("not your turn")

    _assert_square_index(squareIndex)
    if squareIndex == state.holeSquareIndex:
        raise IllegalMove("cannot slide the hole")
    if state.blockedSlideSquareIndex is not None and squareIndex == state.blockedSlideSquareIndex:
        raise IllegalMove("cannot slide the same square as the previous slide")
    if squareIndex not in legal_slide_squares(state):
        raise IllegalMove("square is not adjacent to the hole")

    # Slide into hole = swap the 4-slot arrays; pieces move with the square.
    h = state.holeSquareIndex
    state.board[h], state.board[squareIndex] = state.board[squareIndex], state.board[h]
    state.holeSquareIndex = squareIndex
    # Block moving the same square on the next slide:
    # the moved square now sits at the previous hole index (h).
    state.blockedSlideSquareIndex = h

    w = detect_winner(state)
    if w is not None:
        state.winner = w
        return

    # Turn progression depends on phase
    if state.phase == Phase.placementSlide:
        # slide ends the player's turn
        state.currentPlayer = PlayerColor.B if state.currentPlayer == PlayerColor.R else PlayerColor.R

        # If placement is done for both, switch to movement; otherwise next player places.
        if state.placed[PlayerColor.R] >= state.piecesPerPlayer and state.placed[PlayerColor.B] >= state.piecesPerPlayer:
            state.phase = Phase.movement
        else:
            state.phase = Phase.placement
    else:
        # movement: slide ends turn, next player slides
        state.currentPlayer = PlayerColor.B if state.currentPlayer == PlayerColor.R else PlayerColor.R
        _maybe_set_draw_no_slides(state)


def to_public_json(state: GameState) -> dict:
    return {
        "board": state.board,
        "phase": state.phase.value,
        "currentPlayer": state.currentPlayer.value,
        "placed": {k.value: v for k, v in state.placed.items()},
        "piecesPerPlayer": state.piecesPerPlayer,
        "holeSquareIndex": state.holeSquareIndex,
        # Helpful for clients: which squares can be slid into the hole right now.
        # (Must be left/right/up/down adjacent to holeSquareIndex; diagonals are never included.)
        "legalSlides": legal_slide_squares(state),
        "blockedSlideSquareIndex": state.blockedSlideSquareIndex,
        "winner": state.winner.value if state.winner is not None else None,
        "drawReason": state.drawReason,
    }

