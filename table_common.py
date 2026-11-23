"""Small shared pieces for both rulesets."""

from __future__ import annotations


class GameError(ValueError):
    """A move the player can fix. Handlers return it as data, never a traceback."""


def other(side: str) -> str:
    return "opponent" if side == "player" else "player"


SIDE_LABEL = {"player": "You", "opponent": "Opponent"}
