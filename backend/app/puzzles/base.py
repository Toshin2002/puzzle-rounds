from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any


class Puzzle(ABC):
    """One round's puzzle. Subclass this to add a new puzzle type.

    The server creates a fresh instance at the start of each round. While the round
    is running, only `client_view()` is ever sent to players; the answer never leaves
    the server. `solution_view()` is revealed on the round results screen.
    """

    type: str = "base"        # must match a key in the frontend's puzzle component registry
    title: str = "Puzzle"
    instructions: str = ""
    time_limit: float = 60    # seconds
    max_attempts: int = 3     # wrong guesses allowed before a player is locked out of the round

    def __init__(self, rng: random.Random):
        self.rng = rng

    @abstractmethod
    def client_view(self) -> dict[str, Any]:
        """What players see. Must not contain the answer."""

    @abstractmethod
    def check(self, answer: Any) -> bool:
        """Return True if `answer` (whatever the client sent) is correct."""

    @abstractmethod
    def solution_view(self) -> dict[str, Any]:
        """Shown to everyone after the round. Should include an "answer" string."""

    def score(self, elapsed: float, attempts: int) -> int:
        """Points for a correct answer.

        Default: 500 for solving, plus up to 500 for speed, minus 100 for each wrong
        guess before the right one. Never less than 100 for a correct answer.
        Override this in a subclass if a puzzle needs different scoring.
        """
        time_left = max(0.0, self.time_limit - elapsed)
        speed_bonus = round(500 * time_left / self.time_limit)
        penalty = 100 * (attempts - 1)
        return max(100, 500 + speed_bonus - penalty)
