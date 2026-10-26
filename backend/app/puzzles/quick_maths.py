"""Placeholder puzzle: solve a small arithmetic expression."""

from .base import Puzzle


class QuickMaths(Puzzle):
    type = "quick_maths"
    title = "Quick Maths"
    instructions = "Work out the answer. Whole numbers only."
    time_limit = 30

    def __init__(self, rng):
        super().__init__(rng)
        a = rng.randint(12, 99)
        c = rng.randint(3, 9)
        b = rng.randint(3, 19)
        if rng.random() < 0.5:
            self.expression = f"{a} × {c} + {b}"
            self.answer = a * c + b
        else:
            self.expression = f"{a} × {c} − {b}"
            self.answer = a * c - b

    def client_view(self):
        return {"prompt": self.expression, "input": "number", "placeholder": "Your answer"}

    def check(self, answer):
        try:
            return int(str(answer).strip()) == self.answer
        except ValueError:
            return False

    def solution_view(self):
        return {"answer": str(self.answer), "explanation": f"{self.expression} = {self.answer}"}
