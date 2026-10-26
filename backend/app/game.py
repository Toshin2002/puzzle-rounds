"""The game engine: one Room per game, driven by a server-side state machine.

Phases:  LOBBY -> (ROUND_INTRO -> PLAYING -> ROUND_RESULTS) x rounds -> FINAL

The server is the single source of truth. Clients only ever receive state
snapshots and send back actions ("start", "submit", "back_to_lobby").
"""

from __future__ import annotations

import asyncio
import logging
import random
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .config import Settings
from .puzzles import ROUND_PLAN, make_puzzle
from .puzzles.base import Puzzle

log = logging.getLogger(__name__)


class Phase(str, Enum):
    LOBBY = "lobby"
    ROUND_INTRO = "round_intro"
    PLAYING = "playing"
    ROUND_RESULTS = "round_results"
    FINAL = "final"


class Connection(Protocol):
    """The bits of a WebSocket the room uses (lets tests pass in a fake)."""

    async def send_json(self, data: Any) -> None: ...
    async def close(self, code: int = 1000) -> None: ...


class GameError(Exception):
    """An action the client isn't allowed to take. The message is shown to the player."""


def now() -> float:
    return time.time()


def to_ms(t: float | None) -> int | None:
    return None if t is None else int(t * 1000)


@dataclass
class Submission:
    attempts: int = 0
    correct: bool = False
    finished: bool = False      # solved, or ran out of attempts
    points: int = 0
    elapsed: float | None = None


@dataclass
class Player:
    id: str
    name: str
    token: str                  # secret the browser keeps so it can reconnect to this seat
    ws: Connection | None = None
    score: int = 0
    round_points: list[int] = field(default_factory=list)
    grace_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self.ws is not None


class Room:
    def __init__(self, code: str, settings: Settings):
        self.code = code
        self.settings = settings
        self.players: dict[str, Player] = {}
        self.host_id: str | None = None
        self.phase = Phase.LOBBY
        self.total_rounds = len(ROUND_PLAN)
        self.round_index = -1
        self.puzzle: Puzzle | None = None
        self.round_started_at = 0.0
        self.deadline: float | None = None
        self.submissions: dict[str, Submission] = {}
        self.round_results: list[dict] = []
        self.last_active = now()
        self._round_done = asyncio.Event()
        self._game_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ joining

    async def join(self, ws: Connection, name: str, token: str | None) -> Player:
        self._touch()
        if token:
            existing = next((p for p in self.players.values() if p.token == token), None)
            if existing:
                return await self._reattach(existing, ws)

        name = (name or "").strip()[:20]
        if self.phase != Phase.LOBBY:
            raise GameError("This game has already started.")
        if not name:
            raise GameError("Please enter a name.")
        if len(self.players) >= self.settings.max_players:
            raise GameError("This room is full.")
        if any(p.name.lower() == name.lower() for p in self.players.values()):
            raise GameError("That name is already taken in this room.")

        player = Player(id=secrets.token_hex(4), name=name, token=secrets.token_urlsafe(16), ws=ws)
        self.players[player.id] = player
        if self.host_id not in self.players:
            self.host_id = player.id
        return player

    async def _reattach(self, player: Player, ws: Connection) -> Player:
        if player.grace_task:
            player.grace_task.cancel()
            player.grace_task = None
        old = player.ws
        player.ws = ws
        if old is not None and old is not ws:
            # Same player opened the game in another tab: the newest tab wins.
            await self._send_to(old, {"type": "error", "message": "You opened this game somewhere else.", "fatal": True, "reason": "replaced"})
            try:
                await old.close()
            except Exception:
                pass
        if self.host_id not in self.players:
            self.host_id = player.id
        return player

    async def disconnect(self, player: Player, ws: Connection) -> None:
        if player.ws is not ws:  # an old tab closing after a newer one took over
            return
        player.ws = None
        self._touch()
        player.grace_task = asyncio.create_task(self._grace_expired(player))
        await self.broadcast()
        self._check_round_done()  # don't make everyone wait for someone who left

    async def _grace_expired(self, player: Player) -> None:
        await asyncio.sleep(self.settings.reconnect_grace_seconds)
        player.grace_task = None
        if player.connected:
            return
        if self.phase == Phase.LOBBY:
            self.players.pop(player.id, None)   # left the lobby for good
        if self.host_id == player.id or self.host_id not in self.players:
            self._assign_new_host()
        await self.broadcast()

    def _assign_new_host(self) -> None:
        connected = [p for p in self.players.values() if p.connected]
        if connected:
            self.host_id = connected[0].id
        elif self.host_id not in self.players:
            self.host_id = next(iter(self.players), None)

    # ------------------------------------------------------------------ actions

    async def handle(self, player: Player, msg: dict) -> None:
        self._touch()
        kind = msg.get("type")
        if kind == "start":
            await self.start(player)
        elif kind == "submit":
            await self.submit(player, msg.get("answer"))
        elif kind == "back_to_lobby":
            await self.back_to_lobby(player)
        elif kind == "ping":
            await self._send_to(player.ws, {"type": "pong"})
        else:
            raise GameError(f"Unknown action: {kind!r}")

    async def start(self, player: Player) -> None:
        if player.id != self.host_id:
            raise GameError("Only the host can start the game.")
        if self.phase != Phase.LOBBY:
            raise GameError("The game is already running.")
        for p in self.players.values():
            p.score = 0
            p.round_points = []
        # Leave the lobby immediately so nobody can join or press Start again
        # in the moment before the game loop task begins running.
        self.phase = Phase.ROUND_INTRO
        self._game_task = asyncio.create_task(self._run_game())

    async def back_to_lobby(self, player: Player) -> None:
        """After the final leaderboard, the host can gather everyone for another game."""
        if player.id != self.host_id:
            raise GameError("Only the host can do that.")
        if self.phase != Phase.FINAL:
            raise GameError("The game isn't over yet.")
        for pid in [pid for pid, p in self.players.items() if not p.connected]:
            self.players.pop(pid)
        for p in self.players.values():
            p.score = 0
            p.round_points = []
        self.phase = Phase.LOBBY
        self.round_index = -1
        self.puzzle = None
        self.deadline = None
        self.round_results = []
        await self.broadcast()

    async def submit(self, player: Player, answer: Any) -> None:
        if self.phase != Phase.PLAYING or self.puzzle is None:
            raise GameError("No round is running right now.")
        t = now()
        if self.deadline is not None and t > self.deadline:
            raise GameError("Time's up!")
        sub = self.submissions.setdefault(player.id, Submission())
        if sub.finished:
            raise GameError("You've already finished this round.")

        # Everything from here to the first `await` runs without interruption,
        # so two players submitting at the same instant can't corrupt state.
        sub.attempts += 1
        try:
            correct = bool(self.puzzle.check(answer))
        except Exception:
            log.exception("puzzle.check failed")
            correct = False

        if correct:
            sub.correct = True
            sub.finished = True
            sub.elapsed = t - self.round_started_at
            sub.points = self.puzzle.score(sub.elapsed, sub.attempts)
            feedback = {"type": "feedback", "correct": True, "points": sub.points}
        else:
            attempts_left = self.puzzle.max_attempts - sub.attempts
            if attempts_left <= 0:
                sub.finished = True
            feedback = {"type": "feedback", "correct": False, "attempts_left": max(0, attempts_left)}

        self._check_round_done()
        await self._send_to(player.ws, feedback)
        await self.broadcast()

    # ------------------------------------------------------------------ game loop

    async def _run_game(self) -> None:
        try:
            rng = random.Random(secrets.randbits(64))
            for i in range(self.total_rounds):
                await self._play_round(i, rng)
            self.phase = Phase.FINAL
            self.puzzle = None
            self.deadline = None
            await self.broadcast()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Game loop crashed in room %s", self.code)

    async def _play_round(self, index: int, rng: random.Random) -> None:
        self.round_index = index
        self.puzzle = make_puzzle(index, rng)
        if self.settings.round_seconds_override:
            self.puzzle.time_limit = self.settings.round_seconds_override
        self.submissions = {pid: Submission() for pid in self.players}
        self.round_results = []
        self._round_done = asyncio.Event()

        # 1. Intro: "Round 2 of 5 — Anagram", no puzzle content yet.
        self.phase = Phase.ROUND_INTRO
        self.deadline = now() + self.settings.intro_seconds
        await self.broadcast()
        await asyncio.sleep(self.settings.intro_seconds)

        # 2. Playing: reveal the puzzle to everyone at once and start the clock.
        self.phase = Phase.PLAYING
        self.round_started_at = now()
        self.deadline = self.round_started_at + self.puzzle.time_limit
        await self.broadcast()
        self._check_round_done()
        try:
            await asyncio.wait_for(self._round_done.wait(), timeout=self.puzzle.time_limit)
        except asyncio.TimeoutError:
            pass  # time ran out

        # 3. Results: score the round and show the answer.
        self._finish_round()
        self.phase = Phase.ROUND_RESULTS
        self.deadline = now() + self.settings.results_seconds
        await self.broadcast()
        await asyncio.sleep(self.settings.results_seconds)

    def _check_round_done(self) -> None:
        """End the round early once every connected player has finished."""
        if self.phase != Phase.PLAYING:
            return
        active = [p for p in self.players.values() if p.connected]
        if all(self.submissions.get(p.id, Submission()).finished for p in active):
            self._round_done.set()

    def _finish_round(self) -> None:
        results = []
        for p in self.players.values():
            sub = self.submissions.get(p.id, Submission())
            p.round_points.append(sub.points)
            p.score += sub.points
            results.append({
                "player_id": p.id,
                "name": p.name,
                "correct": sub.correct,
                "points": sub.points,
                "time": None if sub.elapsed is None else round(sub.elapsed, 1),
                "total": p.score,
            })
        results.sort(key=lambda r: (-r["points"], r["time"] if r["time"] is not None else float("inf")))
        self.round_results = results

    # ------------------------------------------------------------------ state

    def _player_status(self, p: Player) -> str | None:
        if self.phase != Phase.PLAYING:
            return None
        sub = self.submissions.get(p.id)
        if sub and sub.correct:
            return "solved"
        if sub and sub.finished:
            return "out"
        return "solving"

    def leaderboard(self) -> list[dict]:
        ordered = sorted(self.players.values(), key=lambda p: (-p.score, p.name.lower()))
        board, last_score, rank = [], None, 0
        for i, p in enumerate(ordered, start=1):
            if p.score != last_score:
                rank, last_score = i, p.score  # ties share a rank: 1, 2, 2, 4
            board.append({"id": p.id, "name": p.name, "score": p.score, "rank": rank, "round_points": p.round_points})
        return board

    def state_for(self, me: Player) -> dict:
        """The snapshot one particular player is allowed to see."""
        players = [
            {
                "id": p.id,
                "name": p.name,
                "score": p.score,
                "connected": p.connected,
                "is_host": p.id == self.host_id,
                "status": self._player_status(p),
            }
            for p in sorted(self.players.values(), key=lambda p: (-p.score, p.name.lower()))
        ]

        puzzle = None
        if self.puzzle and self.phase in (Phase.ROUND_INTRO, Phase.PLAYING, Phase.ROUND_RESULTS):
            puzzle = {
                "type": self.puzzle.type,
                "title": self.puzzle.title,
                "instructions": self.puzzle.instructions,
                "time_limit": self.puzzle.time_limit,
                "max_attempts": self.puzzle.max_attempts,
            }
            if self.phase == Phase.PLAYING:
                puzzle["view"] = self.puzzle.client_view()
            if self.phase == Phase.ROUND_RESULTS:
                puzzle["solution"] = self.puzzle.solution_view()

        my_sub = None
        if self.phase == Phase.PLAYING and self.puzzle:
            sub = self.submissions.get(me.id, Submission())
            my_sub = {
                "attempts": sub.attempts,
                "attempts_left": max(0, self.puzzle.max_attempts - sub.attempts),
                "correct": sub.correct,
                "finished": sub.finished,
                "points": sub.points,
            }

        return {
            "type": "state",
            "code": self.code,
            "phase": self.phase.value,
            "round": self.round_index + 1,
            "total_rounds": self.total_rounds,
            "deadline": to_ms(self.deadline),
            "server_now": to_ms(now()),
            "you": {"id": me.id, "name": me.name, "is_host": me.id == self.host_id},
            "players": players,
            "puzzle": puzzle,
            "my_submission": my_sub,
            "round_results": self.round_results if self.phase == Phase.ROUND_RESULTS else None,
            "leaderboard": self.leaderboard() if self.phase == Phase.FINAL else None,
        }

    async def broadcast(self) -> None:
        targets = [p for p in self.players.values() if p.connected]
        await asyncio.gather(*(self._send_to(p.ws, self.state_for(p)) for p in targets))

    async def _send_to(self, ws: Connection | None, data: dict) -> None:
        if ws is None:
            return
        try:
            await ws.send_json(data)
        except Exception:
            pass  # the socket's own handler will notice and call disconnect()

    # ------------------------------------------------------------------ housekeeping

    def _touch(self) -> None:
        self.last_active = now()

    def is_abandoned(self) -> bool:
        nobody_here = not any(p.connected for p in self.players.values())
        return nobody_here and now() - self.last_active > self.settings.empty_room_ttl_seconds

    def close(self) -> None:
        if self._game_task:
            self._game_task.cancel()
        for p in self.players.values():
            if p.grace_task:
                p.grace_task.cancel()
