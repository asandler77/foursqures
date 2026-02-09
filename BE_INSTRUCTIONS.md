# Four in a Square (ארבע בריבוע) — Python Backend

Backend API for the **"Four in a Square"** marble-and-sliding-tiles game.
The server is the **source of truth** for rules & validation, and plays as the **AI opponent (Blue)**.

---

## Rules implemented

### Board
- 3x3 grid of **squares** (9 total, indexed `0..8`)
- Each square is a **2x2 mini-grid** (4 slots, indexed `0..3`)
- Total: **36 slots**
- **8 tiles + 1 empty slot** (like an 8-puzzle). The empty slot starts at **squareIndex 4** (center).

### Slot layout inside each square

```
 0 | 1
---|---
 2 | 3
```

### Square index layout (3x3)

```
 0 | 1 | 2
---|---|---
 3 | 4 | 5      <-- 4 = initial hole (empty square)
---|---|---
 6 | 7 | 8
```

### Players
- Red = `"R"` -- **Human** (client)
- Blue = `"B"` -- **AI** (server), mode is chosen at game creation
- Red always goes first

### Pieces
- Default: **16 per player** (32 total, configurable via `piecesPerPlayer`, max 16)

### Turn structure

Each turn consists of **two mandatory actions**:

1. **Place** one piece of your color into any **empty slot** (not in the hole square)
2. **Slide** one neighboring square into the **hole** (like 8-puzzle). All pieces inside the square **move with it**.

Only squares **adjacent to the hole** (up/down/left/right) can slide. No diagonals.

### Phases

| Phase | Description |
|-------|-------------|
| `placement` | Player must **place** a piece into an empty slot |
| `placementSlide` | Piece was just placed; player must now **slide** a square into the hole |
| `movement` | All pieces placed; player must only **slide** a square (no placement) |

- When both players placed all pieces, phase becomes `movement`.
- In `movement`, each turn is **only a slide**.

### Win condition
A player wins if they form a **2x2 solid block** of their color **anywhere** on the global **6x6 mini-grid**.

This includes:
- Fully inside **one** square
- Straddling the boundary of **two adjacent** squares
- Spanning the intersection of **four** squares (corners touching)

#### Global coordinate mapping

```
globalRow = squareRow * 2 + miniRow      (0..5)
globalCol = squareCol * 2 + miniCol      (0..5)

squareRow = floor(squareIndex / 3)
squareCol = squareIndex % 3
miniRow   = floor(slotIndex / 2)
miniCol   = slotIndex % 2
```

### No-legal-moves end
In `movement` phase, if the current player has **zero legal slides**, the game ends as **DRAW**.

---

## Run locally

Create a venv, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API will be at `http://127.0.0.1:8000`.

## Tests

```bash
pytest
```

---

## API

### Data model

#### GameState (returned by all endpoints)

```json
{
  "board": [[null, "R", null, null], [null, null, null, null], "...9 arrays total"],
  "phase": "placement",
  "currentPlayer": "R",
  "placed": { "R": 0, "B": 0 },
  "piecesPerPlayer": 8,
  "holeSquareIndex": 4,
  "winner": null,
  "drawReason": null
}
```

- `board`: array of **9** arrays, each with **4** slot values (`null | "R" | "B"`)
- `board[squareIndex][slotIndex]` gives the slot value
- `holeSquareIndex`: which square is the hole (`0..8`)

---

### POST /games -- Create a new game

**Request:**
```json
{
  "piecesPerPlayer": 16,
  "aiMode": "random"
}
```

**Response:**
```json
{
  "gameId": "abc123",
  "playerToken": "tok_xxx",
  "state": { "...GameState..." },
  "aiMode": "random"
}
```

Human = Red (`"R"`), AI = Blue (`"B"`).

---

### GET /games/{game_id} -- Get current state

**Response:**
```json
{
  "state": { "...GameState..." }
}
```

---

### POST /games/{game_id}/move -- Submit a move

The client sends the human's action. The server:
1. Validates and applies the human's action
2. Checks for win/draw
3. If game is not over and it's AI's turn, AI makes its move(s)
4. Returns the updated state (after both human + AI moves)

#### Place a piece (phase = placement)

```json
{
  "action": "place",
  "squareIndex": 0,
  "slotIndex": 2,
  "playerToken": "tok_xxx"
}
```

#### Slide a square (phase = placementSlide or movement)

```json
{
  "action": "slide",
  "squareIndex": 3,
  "playerToken": "tok_xxx"
}
```

`squareIndex` = the square being slid **into the hole** (must be adjacent to `holeSquareIndex`).

#### Success response:
```json
{
  "state": { "...GameState after human move + AI move..." }
}
```

#### Error response:
```json
{
  "error": "Invalid move: slot is occupied"
}
```

---

### POST /games/{game_id}/restart -- Restart the game

**Response:**
```json
{
  "state": { "...fresh GameState..." }
}
```

---

## Client to Server flow

### During placement (each human turn = 2 requests):

```
1. POST /games/{id}/move  { action: "place", squareIndex, slotIndex }
   Server applies placement, returns state with phase: "placementSlide"

2. POST /games/{id}/move  { action: "slide", squareIndex }
   Server applies slide, AI does its turn (place + slide),
   returns state after both players' turns
```

### During movement (each human turn = 1 request):

```
1. POST /games/{id}/move  { action: "slide", squareIndex }
   Server applies slide, AI does its slide,
   returns state after both players' turns
```
