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
        "series_wins": {"blue": 0, "orange": 0},
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

        # Extract score and time
        game = data.get("Game") if isinstance(data, dict) else None
        if game:
            teams = game.get("Teams") or []
            if len(teams) >= 2:
                out["teams"]["blue"] = teams[0].get("Name", out["teams"]["blue"])
                out["teams"]["orange"] = teams[1].get("Name", out["teams"]["orange"])
                out["score"]["blue"] = teams[0].get("Score", 0)
                out["score"]["orange"] = teams[1].get("Score", 0)
                out["series_wins"]["blue"] = teams[0].get("SeriesWins", 0)
                out["series_wins"]["orange"] = teams[1].get("SeriesWins", 0)
            winner = game.get("Winner")
            if winner:
                out["winner"] = winner
            out["time_seconds"] = game.get("TimeSeconds")

    except Exception:
        pass

    return out


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
