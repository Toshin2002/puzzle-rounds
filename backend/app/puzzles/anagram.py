"""Placeholder puzzle: unscramble a word."""

from .base import Puzzle

# Words chosen so their letters don't spell another common word.
WORDS = [
    "puzzle", "rocket", "window", "bridge", "jungle", "pocket", "thunder", "harvest",
    "lantern", "compass", "volcano", "penguin", "diamond", "blanket", "kitchen",
    "monkey", "pumpkin", "dolphin", "picnic", "wizard",
]


class Anagram(Puzzle):
    type = "anagram"
    title = "Anagram"
    instructions = "Unscramble the letters to find the word."
    time_limit = 45

    def __init__(self, rng):
        super().__init__(rng)
        self.word = rng.choice(WORDS)
        letters = list(self.word)
        while "".join(letters) == self.word:
            rng.shuffle(letters)
        self.scrambled = "".join(letters).upper()

    def client_view(self):
        return {
            "prompt": self.scrambled,
            "input": "text",
            "hint": f"{len(self.word)} letters",
            "placeholder": "Type the word",
        }

    def check(self, answer):
        return str(answer).strip().lower() == self.word

    def solution_view(self):
        return {"answer": self.word.upper(), "explanation": f"{self.scrambled} → {self.word.upper()}"}
