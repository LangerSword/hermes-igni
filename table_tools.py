"""The four public tools: table_new, table_play, table_state, table_rules.

Handlers never leak the opponent's hand. A bad move returns JSON the model can
correct instead of raising through the tool boundary.
"""

from __future__ import annotations

import json
from typing import Any

try:  # package import under Hermes
    from . import table_engine, table_store
    from .table_common import GameError
    from .table_render import render
except ImportError:  # standalone
    import table_engine  # type: ignore
    import table_store  # type: ignore
    from table_common import GameError  # type: ignore
    from table_render import render  # type: ignore

TOOLSET = "table"


def _json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _error(message: str, state: dict | None = None) -> str:
    payload: dict[str, Any] = {"error": message}
    if state is not None:
        payload["board"] = render(state)
        module = table_engine.MODES.get(state.get("mode", ""))
        if module is not None:
            payload["hint"] = module.legal_hint(state)
    return _json(payload)


def h_new(args: dict, **_: Any) -> str:
    mode = args.get("mode") or "gwent"
    seed = args.get("seed")
    try:
        seed = int(seed) if seed not in (None, "") else None
    except (TypeError, ValueError):
        return _error("seed must be an integer (or omit it).")
    try:
        state = table_engine.new_game(mode=str(mode), seed=seed)
    except GameError as exc:
        return _error(str(exc))
    table_store.save(state)
    widget = table_store.install_widget()
    message = (
        "Table set. The user is the player — ask for their move. "
        "Relay exactly what they say through table_play; do not move for them."
    )
    if widget.get("ok"):
        message += " TUI scoreboard ready: /table-board."
    return _json(
        {
            "ok": True,
            "game_id": state["game_id"],
            "mode": state["mode"],
            "seed": state["seed"],
            "board": render(state),
            "tui_widget": widget,
            "message": message,
        }
    )


def h_play(args: dict, **_: Any) -> str:
    state = table_store.load_active()
    if state is None:
        return _error("no active table — call table_new first (mode: gwent or arena).")
    action: dict[str, Any] = {"action": args.get("action", "")}
    for key in ("card", "row", "attacker", "target"):
        value = args.get(key)
        if value not in (None, ""):
            action[key] = value
    try:
        state, events = table_engine.apply(state, action)
    except GameError as exc:
        # The state was not committed; show the current board with the reason.
        return _error(str(exc), state)
    table_store.save(state)
    module = table_engine.MODES[state["mode"]]
    return _json(
        {
            "ok": True,
            "events": events,
            "board": render(state),
            "winner": state.get("winner"),
            "hint": module.legal_hint(state),
        }
    )


def h_state(args: dict, **_: Any) -> str:
    state = table_store.load_active()
    if state is None:
        return _json(
            {
                "error": "no active table",
                "message": "Call table_new with mode='gwent' or mode='arena'.",
            }
        )
    return _json(
        {
            "ok": True,
            "game_id": state["game_id"],
            "mode": state["mode"],
            "board": render(state),
            "winner": state.get("winner"),
        }
    )


def h_rules(args: dict, **_: Any) -> str:
    state = table_store.load_active()
    mode = args.get("mode") or (state or {}).get("mode") or "gwent"
    deck = args.get("deck")
    try:
        name, text = table_engine.rules_text(str(mode), deck=str(deck) if deck else None)
    except GameError as exc:
        return _error(str(exc))
    return _json({"ok": True, "mode": name, "rules": text})


_DESCRIPTIONS = {
    "table_new": (
        "Start a card table. mode='gwent' is row warfare (weather, spies, horns, "
        "scorch, best of three); mode='arena' is a 30-health mana duel with taunts, "
        "charge and spells. Call this when the user wants to play. The user is the player."
    ),
    "table_play": (
        "Play ONE move for the user at the active table. Never choose a move on their "
        "behalf: ask what they want and pass exactly that. Gwent: action=play with card "
        "index (and row for a horn), or action=pass. Arena: action=play with card index "
        "(and target for a damage spell), action=attack with attacker and target, or "
        "action=end_turn. Returns the board and the opponent's reply."
    ),
    "table_state": (
        "Show the active card table exactly as the engine has it. The opponent's hand "
        "stays hidden; render the returned board text for the user."
    ),
    "table_rules": (
        "Rules and the card pool for a mode. Use before the first game or when the user "
        "asks what a card does. Defaults to the active table's mode."
    ),
}

_SCHEMAS = {
    "table_new": {
        "name": "table_new",
        "description": _DESCRIPTIONS["table_new"],
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["gwent", "arena"],
                    "description": "gwent (row warfare) or arena (mana duel; accepts 'hearthstone' as an alias).",
                },
                "seed": {
                    "type": "integer",
                    "description": "Optional shuffle seed for a repeatable deal.",
                },
            },
            "required": [],
        },
    },
    "table_play": {
        "name": "table_play",
        "description": _DESCRIPTIONS["table_play"],
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "attack", "pass", "end_turn", "concede"],
                },
                "card": {
                    "type": "integer",
                    "description": "1-based index of the card in your hand (for action=play).",
                },
                "row": {
                    "type": "string",
                    "enum": ["melee", "ranged", "siege"],
                    "description": "Row for Commander's Horn (Gwent).",
                },
                "attacker": {
                    "type": "integer",
                    "description": "1-based index of your minion on the board (Arena attack).",
                },
                "target": {
                    "type": "string",
                    "description": "'hero' or a 1-based enemy board index (Arena attack, damage spell).",
                },
            },
            "required": ["action"],
        },
    },
    "table_state": {
        "name": "table_state",
        "description": _DESCRIPTIONS["table_state"],
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "table_rules": {
        "name": "table_rules",
        "description": _DESCRIPTIONS["table_rules"],
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["gwent", "arena"]},
                "deck": {"type": "string", "description": "Optional faction or deck name."},
            },
            "required": [],
        },
    },
}

TOOL_SPECS = [
    {
        "name": "table_new",
        "handler": h_new,
        "schema": _SCHEMAS["table_new"],
        "description": _DESCRIPTIONS["table_new"],
        "emoji": "🃏",
    },
    {
        "name": "table_play",
        "handler": h_play,
        "schema": _SCHEMAS["table_play"],
        "description": _DESCRIPTIONS["table_play"],
        "emoji": "🎴",
    },
    {
        "name": "table_state",
        "handler": h_state,
        "schema": _SCHEMAS["table_state"],
        "description": _DESCRIPTIONS["table_state"],
        "emoji": "👁️",
    },
    {
        "name": "table_rules",
        "handler": h_rules,
        "schema": _SCHEMAS["table_rules"],
        "description": _DESCRIPTIONS["table_rules"],
        "emoji": "📖",
    },
]

TOOL_NAMES = [spec["name"] for spec in TOOL_SPECS]
