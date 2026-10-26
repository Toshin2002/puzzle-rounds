import random

from .anagram import Anagram
from .base import Puzzle
from .quick_maths import QuickMaths

# Every puzzle type the server knows about, keyed by its `type`.
PUZZLE_TYPES: dict[str, type[Puzzle]] = {cls.type: cls for cls in (QuickMaths, Anagram)}

# Which puzzle type each round uses. The game has as many rounds as this list.
# These are placeholders until we choose the real puzzles.
ROUND_PLAN: list[str] = ["quick_maths", "anagram", "quick_maths", "anagram", "quick_maths"]


def make_puzzle(round_index: int, rng: random.Random) -> Puzzle:
    return PUZZLE_TYPES[ROUND_PLAN[round_index]](rng)
