"""Mode dispatch shared by the tools, the slash command, the CLI and the widget."""

from __future__ import annotations

try:  # package import under Hermes
    from . import table_arena, table_gwent
    from .table_cards import card_list_for, rules_for
    from .table_common import GameError
    from .table_render import public_view, render, snapshot
except ImportError:  # standalone
    import table_arena  # type: ignore
    import table_gwent  # type: ignore
    from table_cards import card_list_for, rules_for  # type: ignore
    from table_common import GameError  # type: ignore
    from table_render import public_view, render, snapshot  # type: ignore

MODES = {"gwent": table_gwent, "arena": table_arena}
ALIASES = {
    "gwent": "gwent",
    "witcher": "gwent",
    "rows": "gwent",
    "arena": "arena",
    "hearthstone": "arena",
    "hs": "arena",
    "duel": "arena",
}


def normalize_mode(mode: str | None) -> str:
    key = (mode or "gwent").strip().lower()
    if key not in ALIASES:
        raise GameError(
            f"unknown mode {mode!r}; choose 'gwent' (row warfare) or "
            "'arena' (mana duel, Hearthstone-shaped)."
        )
    return ALIASES[key]


def new_game(mode: str | None = "gwent", seed: int | None = None) -> dict:
    name = normalize_mode(mode)
    if name == "gwent":
        return table_gwent.new_game(seed=seed)
    return table_arena.new_game(seed=seed)


def apply(state: dict, action: dict, auto: bool = True) -> tuple[dict, list[str]]:
    module = MODES.get(state.get("mode", ""))
    if module is None:
        raise GameError(f"unknown table mode {state.get('mode')!r}.")
    state, events = module.apply(state, action)
    # Gwent is one action per side; the opponent answers inside the same call so
    # a chat turn never ends on "opponent to move" with nobody to move it.
    if auto and state.get("mode") == "gwent" and not state.get("winner"):
        guard = 0
        while state["turn"] == "opponent" and not state.get("winner") and guard < 300:
            ai_move = table_gwent.ai_action(state, "opponent")
            state, reply = table_gwent.apply(state, ai_move)
            events = events + reply
            guard += 1
    return state, events


def render_board(state: dict, reveal: bool = False) -> str:
    return render(state, reveal=reveal)


def board_snapshot(state: dict) -> dict:
    return snapshot(state)


def rules_text(mode: str | None = None, deck: str | None = None) -> tuple[str, str]:
    name = normalize_mode(mode)
    return name, rules_for(name) + "\n\n" + card_list_for(name, deck)


__all__ = [
    "GameError",
    "MODES",
    "apply",
    "board_snapshot",
    "new_game",
    "normalize_mode",
    "public_view",
    "render_board",
    "rules_text",
]
