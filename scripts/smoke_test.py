import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, body=None):
    url = BASE + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> int:
    st, out = req("GET", "/health")
    print("health:", st, out)

    st, out = req("POST", "/games", {"pieceLimitPerPlayer": 2})
    game_id = out["game_id"]
    r_token = out["player_token"]
    print("create:", st, game_id, out["color"])

    st, out = req("POST", f"/games/{game_id}/join")
    b_token = out["player_token"]
    print("join:", st, out["color"])

    st, out = req(
        "POST",
        f"/games/{game_id}/move",
        {"player_token": r_token, "place": {"bigRow": 0, "bigCol": 0, "miniRow": 0, "miniCol": 0}},
    )
    print("R place:", st, "phase", out["state"]["phase"], "turn", out["state"]["turn"])

    st, out = req(
        "POST",
        f"/games/{game_id}/move",
        {"player_token": b_token, "place": {"bigRow": 2, "bigCol": 2, "miniRow": 1, "miniCol": 1}},
    )
    print("B place:", st, "phase", out["state"]["phase"], "turn", out["state"]["turn"])

    st, out = req("GET", f"/games/{game_id}")
    print("get:", st, "status", out["state"]["status"], "rev", out["state"]["revision"])

    st, out = req("POST", f"/games/{game_id}/restart", {"player_token": r_token})
    print("restart:", st, "phase", out["state"]["phase"], "placed", out["state"]["placedCount"])

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

