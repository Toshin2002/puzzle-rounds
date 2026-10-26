"""Engine tests. They drive a Room directly with fake sockets and very short timers.

Run from the backend folder:  python -m pytest -q
"""

import asyncio

import pytest

from app.config import Settings
from app.game import GameError, Room

FAST = Settings(intro_seconds=0.01, results_seconds=0.01, round_seconds_override=0.4, reconnect_grace_seconds=0.05)


class FakeWS:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed = True

    def last_state(self):
        return next(m for m in reversed(self.sent) if m["type"] == "state")


async def wait_for_phase(room, phase, timeout=3):
    """Wait until the room is in `phase` and every connected player has been told."""
    for _ in range(int(timeout / 0.005)):
        told = all(
            p.ws.last_state()["phase"] == phase
            for p in room.players.values() if p.connected and p.ws.sent
        )
        if room.phase.value == phase and told:
            return
        await asyncio.sleep(0.005)
    raise AssertionError(f"room never reached {phase}, stuck in {room.phase}")


def answer(room):
    return room.puzzle.solution_view()["answer"]


def test_full_game_solver_vs_wrong_guesser():
    async def run():
        room = Room("TEST", FAST)
        ws1, ws2 = FakeWS(), FakeWS()
        alice = await room.join(ws1, "Alice", None)
        bob = await room.join(ws2, "Bob", None)
        assert room.host_id == alice.id

        await room.start(alice)
        for _ in range(room.total_rounds):
            await wait_for_phase(room, "playing")
            # The puzzle sent to players must never contain the answer.
            view = ws1.last_state()["puzzle"]["view"]
            assert "answer" not in view and "solution" not in ws1.last_state()["puzzle"]
            await room.submit(alice, answer(room))
            for _ in range(room.puzzle.max_attempts):
                await room.submit(bob, "definitely wrong")
            # Both finished, so the round should end early without waiting for the timer.
            await wait_for_phase(room, "round_results", timeout=0.2)
            assert ws1.last_state()["round_results"][0]["name"] == "Alice"
        await wait_for_phase(room, "final")

        board = ws2.last_state()["leaderboard"]
        assert [row["name"] for row in board] == ["Alice", "Bob"]
        assert board[0]["score"] > 0 and board[1]["score"] == 0
        assert len(board[0]["round_points"]) == 5
        assert all(p >= 100 for p in board[0]["round_points"])
    asyncio.run(run())


def test_round_ends_on_timer_when_nobody_answers():
    async def run():
        room = Room("TIME", FAST)
        host = await room.join(FakeWS(), "Host", None)
        await room.start(host)
        await wait_for_phase(room, "playing")
        await wait_for_phase(room, "round_results", timeout=1)
        assert room.round_results[0]["points"] == 0
        room.close()
    asyncio.run(run())


def test_rules_are_enforced():
    async def run():
        room = Room("RULE", FAST)
        host = await room.join(FakeWS(), "Host", None)
        guest = await room.join(FakeWS(), "Guest", None)
        with pytest.raises(GameError):
            await room.join(FakeWS(), "host", None)        # duplicate name
        with pytest.raises(GameError):
            await room.start(guest)                        # only host starts
        with pytest.raises(GameError):
            await room.submit(host, "1")                   # no round yet
        await room.start(host)
        with pytest.raises(GameError):
            await room.join(FakeWS(), "Late", None)        # game in progress
        await wait_for_phase(room, "playing")
        await room.submit(host, answer(room))
        with pytest.raises(GameError):
            await room.submit(host, answer(room))          # can't score twice
        room.close()
    asyncio.run(run())


def test_reconnect_keeps_seat_and_score():
    async def run():
        room = Room("BACK", FAST)
        ws_old = FakeWS()
        p = await room.join(ws_old, "Alice", None)
        other = await room.join(FakeWS(), "Bob", None)
        await room.start(p)
        await wait_for_phase(room, "playing")
        await room.submit(p, answer(room))
        await room.disconnect(p, ws_old)
        assert not p.connected
        ws_new = FakeWS()
        again = await room.join(ws_new, "", p.token)       # token, no name needed
        assert again is p and p.connected
        await room.broadcast()
        assert ws_new.last_state()["my_submission"]["correct"] is True
        room.close()
        _ = other
    asyncio.run(run())


def test_lobby_leaver_removed_and_host_passed_on():
    async def run():
        room = Room("LEAV", FAST)
        ws = FakeWS()
        host = await room.join(ws, "Host", None)
        guest = await room.join(FakeWS(), "Guest", None)
        await room.disconnect(host, ws)
        await asyncio.sleep(0.1)  # longer than the grace period
        assert host.id not in room.players
        assert room.host_id == guest.id
    asyncio.run(run())
