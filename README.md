# Puzzle Rounds

A live multiplayer game: players join a room with a 4-letter code, play 5 timed puzzle rounds together, and see a final leaderboard.

- **Backend:** FastAPI + WebSockets (Python 3.10+)
- **Frontend:** React + Vite (plain JavaScript)

The two puzzles included (Quick Maths and Anagram) are placeholders to exercise the engine. Swapping in real puzzles is covered below.

## Run it locally

You need two terminals.

**1. Backend** (port 8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**2. Frontend** (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. To play against yourself, open a second browser window in private/incognito mode (each window needs its own storage) and join with the room code.

**Testing faster:** shorten the timers with environment variables:

```bash
INTRO_SECONDS=1 RESULTS_SECONDS=2 ROUND_SECONDS_OVERRIDE=10 uvicorn app.main:app --reload
```

**Run the engine tests:** `cd backend && python -m pytest -q`

**Play on your phone on the same Wi-Fi:** run `npm run dev -- --host` and open the "Network" address it prints.

## How it works

```
LOBBY ──start──▶ ROUND_INTRO ──▶ PLAYING ──▶ ROUND_RESULTS ──┐
                      ▲                                       │ ×5
                      └───────────────────────────────────────┘
                                                      ──▶ FINAL ──play again──▶ LOBBY
```

- **The server is the source of truth.** Each room (`backend/app/game.py`) runs an `asyncio` loop that moves through the phases, owns the timers, checks answers and adds up scores. The browser only displays what the server sends and sends back actions.
- **Answers never reach the browser.** During a round, players get only `client_view()`. The solution is revealed on the results screen.
- **Timers are deadlines.** The server sends "round ends at <timestamp>"; each browser draws its own countdown, corrected for clock difference. No one can stretch their time, since the server rejects late answers.
- **Rounds end early** once every connected player has solved it or used up their tries.
- **Scoring (default):** 500 for a correct answer + up to 500 speed bonus − 100 per wrong guess before it (minimum 100). Points are added at the end of each round. Ties share a rank.
- **Reconnection:** on joining, the server gives the browser a secret token (kept in `localStorage`). A refresh or dropped connection rejoins the same seat with the score intact. Someone who leaves the lobby loses their seat after 15 seconds, and if the host leaves, another player becomes host.

## Project layout

```
backend/
  app/
    main.py          FastAPI app: REST endpoints + the WebSocket endpoint
    game.py          Room, Player, phases, game loop, scoring, state snapshots
    config.py        Timer settings (overridable with env vars)
    puzzles/
      base.py        The Puzzle base class every puzzle implements
      quick_maths.py placeholder
      anagram.py     placeholder
      __init__.py    PUZZLE_TYPES registry + ROUND_PLAN (which puzzle each round uses)
  tests/test_game.py
frontend/
  src/
    useGame.js       WebSocket connection, reconnects, latest state
    useCountdown.js  Server-synced countdown
    session.js       localStorage + ?room= URL helpers
    App.jsx          Picks the screen for the current phase
    components/      Home, Lobby, RoundIntro, Playing, RoundResults, FinalLeaderboard, Timer
    components/puzzles/
      index.js             Maps puzzle type → React component
      TextAnswerPuzzle.jsx Generic "prompt + answer box" UI
```

## Adding a real puzzle

1. **Backend:** create `backend/app/puzzles/my_puzzle.py` with a subclass of `Puzzle`:
   - `type`, `title`, `instructions`, `time_limit`, `max_attempts`
   - `__init__(rng)`: generate the puzzle (use `rng` for randomness)
   - `client_view()`: what players see (no answer in here)
   - `check(answer)`: return `True` if correct
   - `solution_view()`: `{"answer": ..., "explanation": ...}` for the results screen
   - optionally override `score(elapsed, attempts)`
2. Register it in `puzzles/__init__.py` (`PUZZLE_TYPES`) and put its `type` into `ROUND_PLAN`.
3. **Frontend:** if a text box is enough, you're done. `TextAnswerPuzzle` will render it. For a custom UI (a grid, dragging tiles…), write a component that takes `{ view, disabled, onSubmit }` and add it to `REGISTRY` in `components/puzzles/index.js`. Whatever you pass to `onSubmit(answer)` arrives in `check(answer)` on the server.

## WebSocket messages

Client → server:

| type | fields | when |
|---|---|---|
| `join` | `name`, `token` (or null) | first message after connecting |
| `start` | | host, in the lobby |
| `submit` | `answer` | during a round |
| `back_to_lobby` | | host, on the final screen |

Server → client: `joined` (your id + token), `state` (full snapshot, sent after every change), `feedback` (result of your answer), `error` (`fatal: true` means you've been disconnected).

## Deploying

`npm run build` in `frontend/` creates `frontend/dist`. When that folder exists, FastAPI serves the frontend itself, so you deploy a single service (for example on Render, Railway or Fly.io) with the start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` run from `backend/`.

Rooms live in memory, so run **one** server process. That comfortably handles many simultaneous rooms. To scale to several processes later, move room state into Redis.
