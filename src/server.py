from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import asyncio
import json
import os
from typing import Set

from src.streamer import stream_rl

app = FastAPI()

# Shared state
clients: Set[WebSocket] = set()
latest_state = {}
state_lock = asyncio.Lock()
test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
series_state = {
    "match_guid": None,
    "series_wins": {"blue": 0, "orange": 0},
    "last_game_finished": False,
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_PATH, exist_ok=True)
PARSED_FILE = os.path.join(DATA_PATH, "parsed_state.json")
IMAGE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "templates", "images", "image.png"
)
GAMEPLAY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "templates", "images", "gameplay.png"
)
VITALITY_LOGO_PATH = os.path.join(
    os.path.dirname(__file__), "..", "templates", "images", "logo_vitality.png"
)
NRG_LOGO_PATH = os.path.join(
    os.path.dirname(__file__), "..", "templates", "images", "logo_nrg.png"
)
BOURGEOIS_BOLD_ITALIC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "templates", "images", "Bourgeois-BoldItalic.ttf"
)


def load_template(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "templates", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Template not found</h1>"


async def parse_and_broadcast(queue: asyncio.Queue):
    """Consume raw events from queue, extract fields and broadcast to WS clients."""
    while True:
        event = await queue.get()
        try:
            parsed = parse_event(event)
            parsed = apply_series_state(parsed)
            # update in-memory state and write to file
            async with state_lock:
                latest_state.clear()
                latest_state.update(parsed)
                try:
                    with open(PARSED_FILE, "w", encoding="utf-8") as f:
                        json.dump(latest_state, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            # broadcast to websocket clients
            dead = []
            payload = json.dumps(parsed, ensure_ascii=False)
            for ws in list(clients):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                try:
                    clients.remove(ws)
                except KeyError:
                    pass
        finally:
            queue.task_done()


def parse_event(event: dict) -> dict:
    """Parse an incoming event object and return a simplified state dict.

    Expected event examples seen in the overlay are like:
    {"Event":"UpdateState", "Data":"{...json...}"}
    where `Data` may itself be a JSON-encoded string.
    """
    out = {
        "players": [],
        "score": {"blue": 0, "orange": 0},
        "teams": {"blue": "Blue", "orange": "Orange"},
        "series_wins": None,
        "is_overtime": False,
        "match_guid": None,
        "game_has_winner": False,
        "winner": None,
        "time_seconds": None,
    }

    try:
        # If Data is a JSON string, parse it
        data = event.get("Data") if isinstance(event, dict) else None
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                # sometimes it's already an object stringified twice; try trimming
                data = json.loads(data)

        if not data and isinstance(event, dict):
            # fallback: the event might already be the inner object
            data = event.get("Data") or event

        # Extract players
        players = data.get("Players") if isinstance(data, dict) else None
        if players:
            out["players"] = players

        # Extract score, overtime and time
        game = data.get("Game") if isinstance(data, dict) else None
        if game:
            out["match_guid"] = data.get("MatchGuid") or game.get("MatchGuid")
            teams = game.get("Teams") or []
            if len(teams) >= 2:
                out["teams"]["blue"] = teams[0].get("Name", out["teams"]["blue"])
                out["teams"]["orange"] = teams[1].get("Name", out["teams"]["orange"])
                out["score"]["blue"] = teams[0].get("Score", 0)
                out["score"]["orange"] = teams[1].get("Score", 0)
                if any("SeriesWins" in team for team in teams):
                    out["series_wins"] = {
                        "blue": teams[0].get("SeriesWins", 0),
                        "orange": teams[1].get("SeriesWins", 0),
                    }
            out["game_has_winner"] = bool(game.get("bHasWinner")) or bool(
                game.get("Winner")
            )
            winner = game.get("Winner")
            if winner:
                out["winner"] = winner
            out["time_seconds"] = game.get("TimeSeconds")
            out["is_overtime"] = bool(game.get("bOvertime") or game.get("IsOT"))
        elif isinstance(data, dict):
            out["match_guid"] = data.get("MatchGuid")
            out["time_seconds"] = data.get("TimeSeconds")
            out["is_overtime"] = bool(data.get("bOvertime") or data.get("IsOT"))
            out["game_has_winner"] = bool(data.get("bHasWinner")) or bool(
                data.get("Winner")
            )

    except Exception:
        pass

    return out


def apply_series_state(parsed: dict) -> dict:
    """Derive series wins from match state when the source does not provide them."""
    match_guid = parsed.get("match_guid")
    if match_guid and series_state["match_guid"] != match_guid:
        series_state["match_guid"] = match_guid
        series_state["series_wins"] = {"blue": 0, "orange": 0}
        series_state["last_game_finished"] = False

    # Prefer source-provided series wins if present, otherwise keep our derived count.
    source_series_wins = parsed.get("series_wins") or {}
    source_blue = source_series_wins.get("blue")
    source_orange = source_series_wins.get("orange")
    has_source_wins = parsed.get("series_wins") is not None

    game_finished = bool(parsed.get("game_has_winner"))

    if not has_source_wins:
        if game_finished and not series_state["last_game_finished"]:
            score = parsed.get("score") or {"blue": 0, "orange": 0}
            blue_score = int(score.get("blue", 0) or 0)
            orange_score = int(score.get("orange", 0) or 0)
            if blue_score > orange_score:
                series_state["series_wins"]["blue"] += 1
            elif orange_score > blue_score:
                series_state["series_wins"]["orange"] += 1
        parsed["series_wins"] = dict(series_state["series_wins"])
    else:
        series_state["series_wins"] = {
            "blue": int(source_blue or 0),
            "orange": int(source_orange or 0),
        }
        parsed["series_wins"] = dict(series_state["series_wins"])

    series_state["last_game_finished"] = game_finished
    return parsed


@app.on_event("startup")
async def startup_event():
    # create queue and start producer + parser
    app.state.queue = asyncio.Queue()
    app.state.producer = asyncio.create_task(
        stream_rl(app.state.queue, host="127.0.0.1", port=49123, test_mode=test_mode)
    )
    app.state.parser = asyncio.create_task(parse_and_broadcast(app.state.queue))


@app.on_event("shutdown")
async def shutdown_event():
    # cancel tasks
    for tname in ("producer", "parser"):
        t = getattr(app.state, tname, None)
        if t:
            t.cancel()


@app.get("/")
async def index():
    return HTMLResponse(load_template("template.html"))


@app.get("/overlay")
async def overlay():
    return HTMLResponse(load_template("overlay.html"))


@app.get("/image.png")
async def overlay_image():
    return FileResponse(IMAGE_PATH, media_type="image/png")


@app.get("/gameplay.png")
async def gameplay_image():
    return FileResponse(GAMEPLAY_PATH, media_type="image/png")


@app.get("/logo_vitality.png")
async def vitality_logo():
    return FileResponse(VITALITY_LOGO_PATH, media_type="image/png")


@app.get("/logo_nrg.png")
async def nrg_logo():
    return FileResponse(NRG_LOGO_PATH, media_type="image/png")


@app.get("/Bourgeois-BoldItalic.ttf")
async def bourgeois_bold_italic():
    return FileResponse(BOURGEOIS_BOLD_ITALIC_PATH, media_type="font/ttf")


@app.get("/state")
async def state():
    async with state_lock:
        return JSONResponse(latest_state)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        # send current state on connect
        async with state_lock:
            if latest_state:
                await websocket.send_text(json.dumps(latest_state, ensure_ascii=False))

        while True:
            # keep connection open; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            clients.remove(websocket)
        except KeyError:
            pass
    except Exception:
        try:
            clients.remove(websocket)
        except Exception:
            pass
