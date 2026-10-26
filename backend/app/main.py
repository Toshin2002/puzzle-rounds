"""FastAPI entry point: a small REST API for rooms plus one WebSocket per player.

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .game import GameError, Phase, Room

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("puzzle-rounds")

settings = load_settings()
rooms: dict[str, Room] = {}

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I mix-ups


def new_room_code() -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))
        if code not in rooms:
            return code


async def sweep_abandoned_rooms() -> None:
    while True:
        await asyncio.sleep(60)
        for code, room in list(rooms.items()):
            if room.is_abandoned():
                room.close()
                rooms.pop(code, None)
                log.info("Removed abandoned room %s", code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweeper = asyncio.create_task(sweep_abandoned_rooms())
    yield
    sweeper.cancel()
    for room in rooms.values():
        room.close()


app = FastAPI(title="Puzzle Rounds", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True, "rooms": len(rooms)}


@app.post("/api/rooms")
async def create_room():
    code = new_room_code()
    rooms[code] = Room(code, settings)
    log.info("Created room %s", code)
    return {"code": code}


@app.get("/api/rooms/{code}")
async def room_info(code: str):
    room = rooms.get(code.upper())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": len(room.players),
        "joinable": room.phase == Phase.LOBBY,
    }


async def _reject(ws: WebSocket, message: str) -> None:
    await ws.send_json({"type": "error", "message": message, "fatal": True})
    await ws.close()


@app.websocket("/ws/{code}")
async def game_socket(ws: WebSocket, code: str):
    await ws.accept()
    room = rooms.get(code.upper())
    if room is None:
        await _reject(ws, "Room not found. Check the code and try again.")
        return

    # The first message must be: {"type": "join", "name": "...", "token": "..." | null}
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=10))
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError):
        await ws.close()
        return
    if not isinstance(hello, dict) or hello.get("type") != "join":
        await _reject(ws, "Expected a join message first.")
        return

    try:
        player = await room.join(ws, str(hello.get("name") or ""), hello.get("token"))
    except GameError as e:
        await _reject(ws, str(e))
        return

    await ws.send_json({"type": "joined", "player_id": player.id, "token": player.token})
    await room.broadcast()

    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > 4096:
                continue  # ignore oversized messages
            try:
                msg = json.loads(raw)
                if not isinstance(msg, dict):
                    raise ValueError
                await room.handle(player, msg)
            except ValueError:
                await ws.send_json({"type": "error", "message": "Malformed message."})
            except GameError as e:
                await ws.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error in room %s", room.code)
    finally:
        await room.disconnect(player, ws)


# In production, serve the built React app from the same server (one thing to deploy).
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
