import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, body=None):
    url = BASE + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> None:
    st, out = req("GET", "/health")
    print("health:", st, out)

    st, out = req("POST", "/games", {"piecesPerPlayer": 2})
    game_id = out["gameId"]
    token = out["playerToken"]
    print("create:", st, game_id, "phase", out["state"]["phase"])

    # 1) place (should NOT trigger AI, should switch to placementSlide)
    st, out = req(
        "POST",
        f"/games/{game_id}/move",
        {"action": "place", "squareIndex": 0, "slotIndex": 0, "playerToken": token},
    )
    print("place:", st, "phase", out["state"]["phase"], "currentPlayer", out["state"]["currentPlayer"])

    # 2) slide (should trigger AI place+slide, returning to human)
    st, out = req(
        "POST",
        f"/games/{game_id}/move",
        {"action": "slide", "squareIndex": 3, "playerToken": token},
    )
    print("slide:", st, "phase", out["state"]["phase"], "currentPlayer", out["state"]["currentPlayer"])
    print("placed:", out["state"]["placed"], "hole:", out["state"]["holeSquareIndex"])

    # restart
    st, out = req("POST", f"/games/{game_id}/restart", {"playerToken": token})
    print("restart:", st, "phase", out["state"]["phase"], "hole", out["state"]["holeSquareIndex"])

    print("OK")


if __name__ == "__main__":
    main()

