import pytest

from app.game_logic import (
    IllegalMove,
    Phase,
    PlayerColor,
    apply_place,
    apply_slide,
    detect_winner,
    legal_slide_squares,
    new_state,
)


def test_new_game_defaults() -> None:
    s = new_state()
    assert s.holeSquareIndex == 4
    assert s.phase == Phase.placement
    assert s.currentPlayer == PlayerColor.R
    assert s.placed[PlayerColor.R] == 0
    assert s.placed[PlayerColor.B] == 0


def test_place_then_requires_slide_same_player() -> None:
    s = new_state(pieces_per_player=1)
    apply_place(s, squareIndex=0, slotIndex=2, player=PlayerColor.R)
    assert s.phase == Phase.placementSlide
    assert s.currentPlayer == PlayerColor.R

    with pytest.raises(IllegalMove):
        # cannot place again; must slide
        apply_place(s, squareIndex=0, slotIndex=3, player=PlayerColor.R)


def test_slide_swaps_square_contents_and_moves_hole() -> None:
    s = new_state(pieces_per_player=1)
    apply_place(s, squareIndex=1, slotIndex=0, player=PlayerColor.R)
    assert s.holeSquareIndex == 4

    # slide square 1 into hole 4 (adjacent)
    apply_slide(s, squareIndex=1, player=PlayerColor.R)
    assert s.holeSquareIndex == 1
    # piece should have moved with the square into old hole position (4)
    assert s.board[4][0] == "R"
    assert s.board[1] == [None, None, None, None]


def test_movement_phase_after_all_pieces_placed() -> None:
    s = new_state(pieces_per_player=1)
    apply_place(s, squareIndex=0, slotIndex=0, player=PlayerColor.R)
    apply_slide(s, squareIndex=3, player=PlayerColor.R)  # any legal slide
    apply_place(s, squareIndex=8, slotIndex=3, player=PlayerColor.B)
    apply_slide(s, squareIndex=0, player=PlayerColor.B)
    assert s.phase == Phase.movement


def test_win_detection_allows_crossing_four_squares() -> None:
    s = new_state(pieces_per_player=8)
    # create 2x2 at global (1,1),(1,2),(2,1),(2,2) which touches 4 squares
    # mapping: (1,1)->sq0 slot3 ; (1,2)->sq1 slot2 ; (2,1)->sq3 slot1 ; (2,2)->sq4 slot0
    s.board[0][3] = "R"
    s.board[1][2] = "R"
    s.board[3][1] = "R"
    s.board[4][0] = "R"
    assert detect_winner(s) == PlayerColor.R


def test_slide_only_adjacent_to_hole() -> None:
    s = new_state()
    adj = set(legal_slide_squares(s))
    assert adj == {1, 3, 5, 7}

    with pytest.raises(IllegalMove):
        apply_slide(s, squareIndex=0, player=PlayerColor.R)


def test_cannot_slide_same_square_as_previous_slide() -> None:
    # Reach movement phase quickly (1 piece each), then verify backtracking is blocked.
    s = new_state(pieces_per_player=1)
    apply_place(s, squareIndex=0, slotIndex=0, player=PlayerColor.R)
    apply_slide(s, squareIndex=3, player=PlayerColor.R)  # hole: 4 -> 3
    apply_place(s, squareIndex=8, slotIndex=0, player=PlayerColor.B)
    apply_slide(s, squareIndex=0, player=PlayerColor.B)  # hole: 3 -> 0 (movement starts, R turn)
    assert s.phase == Phase.movement
    assert s.currentPlayer == PlayerColor.R

    # R slides square 1 into hole 0 => moved square now sits at index 0, and must be blocked next.
    apply_slide(s, squareIndex=1, player=PlayerColor.R)  # hole: 0 -> 1
    assert s.currentPlayer == PlayerColor.B

    # B would normally be able to slide square 0 into hole 1 (immediate backtrack), but it's forbidden.
    with pytest.raises(IllegalMove):
        apply_slide(s, squareIndex=0, player=PlayerColor.B)
