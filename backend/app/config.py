"""Game settings. Override any of these with environment variables (handy for testing)."""

import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    intro_seconds: float = 4            # "Round 2 of 5" screen before the puzzle appears
    results_seconds: float = 8          # round results screen before the next round
    round_seconds_override: float | None = None  # force every round to this length (testing)
    reconnect_grace_seconds: float = 15  # how long a dropped player keeps their seat in the lobby / host role
    max_players: int = 20
    empty_room_ttl_seconds: float = 300  # delete rooms nobody has been connected to for this long


def load_settings() -> Settings:
    override = os.getenv("ROUND_SECONDS_OVERRIDE")
    return Settings(
        intro_seconds=_float("INTRO_SECONDS", 4),
        results_seconds=_float("RESULTS_SECONDS", 8),
        round_seconds_override=float(override) if override else None,
        reconnect_grace_seconds=_float("RECONNECT_GRACE_SECONDS", 15),
    )
