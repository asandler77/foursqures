from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .ai import ai_take_turn
from .game_logic import IllegalMove, PlayerColor, apply_place, apply_slide, new_state, to_public_json
from .schemas import CreateGameIn, CreateGameOut, GameStateOut, MoveIn, RestartIn
from .store import store

app = FastAPI(title="Arba BaRibua (Four in a Square) API")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/games", response_model=CreateGameOut)
def create_game(body: CreateGameIn) -> CreateGameOut:
    g = store.create_game(pieces_per_player=body.piecesPerPlayer)
    return CreateGameOut(
        gameId=g.id,
        playerToken=g.red.token,
        state=to_public_json(g.state),
    )


@app.get("/games/{game_id}", response_model=GameStateOut)
def get_game(game_id: str) -> GameStateOut:
    try:
        g = store.get_game(game_id)
        return GameStateOut(state=to_public_json(g.state))
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "game not found"})


@app.post("/games/{game_id}/move", response_model=GameStateOut)
async def move(game_id: str, body: MoveIn) -> GameStateOut:
    try:
        g = store.get_game(game_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "game not found"})

    async with g.lock:
        try:
            p = store.resolve_player(g, body.playerToken)
        except PermissionError:
            raise HTTPException(status_code=401, detail={"error": "invalid playerToken"})

        try:
            player = PlayerColor(p.color.value)
            if body.action == "place":
                assert body.slotIndex is not None
                assert body.squareIndex is not None
                apply_place(g.state, squareIndex=body.squareIndex, slotIndex=body.slotIndex, player=player)
                # Optional: allow client to include the required slide in the same request
                if body.slideSquareIndex is not None and g.state.winner is None and g.state.drawReason is None:
                    apply_slide(g.state, squareIndex=body.slideSquareIndex, player=player)
            else:
                # Support slide payload styles:
                # A) New client: {fromSquareIndex, toHoleSquareIndex}
                if body.toHoleSquareIndex is not None:
                    assert body.fromSquareIndex is not None
                    if body.toHoleSquareIndex != g.state.holeSquareIndex:
                        raise IllegalMove("toHoleSquareIndex must equal the current holeSquareIndex")
                    apply_slide(g.state, squareIndex=body.fromSquareIndex, player=player)
                # B) Legacy-alt: {squareIndex: hole, fromSquareIndex}
                elif body.fromSquareIndex is not None:
                    assert body.squareIndex is not None
                    if body.squareIndex != g.state.holeSquareIndex:
                        raise IllegalMove("squareIndex must equal the current holeSquareIndex when using fromSquareIndex")
                    apply_slide(g.state, squareIndex=body.fromSquareIndex, player=player)
                # C) Legacy: {squareIndex: fromSquareIndex}
                else:
                    assert body.squareIndex is not None
                    apply_slide(g.state, squareIndex=body.squareIndex, player=player)
        except IllegalMove as e:
            # Match BE_INSTRUCTIONS error shape (no "detail" wrapper)
            return JSONResponse(status_code=400, content={"error": f"Invalid move: {str(e)}"})

        # After a human slide, it may become AI's turn; AI should play automatically.
        if g.state.winner is None and g.state.drawReason is None:
            ai_take_turn(g.state)

        return GameStateOut(state=to_public_json(g.state))


@app.post("/games/{game_id}/restart", response_model=GameStateOut)
async def restart(game_id: str, body: RestartIn) -> GameStateOut:
    try:
        g = store.get_game(game_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "game not found"})

    async with g.lock:
        try:
            _ = store.resolve_player(g, body.playerToken)
        except PermissionError:
            raise HTTPException(status_code=401, detail={"error": "invalid playerToken"})

        g.state = new_state(pieces_per_player=g.state.piecesPerPlayer)
        return GameStateOut(state=to_public_json(g.state))

