"""Text rendering. One board string serves chat, the CLI and the TUI widget."""

from __future__ import annotations

try:  # package import under Hermes
    from . import table_arena, table_gwent
    from .table_cards import GWENT_FACTIONS, GWENT_WEATHER
except ImportError:  # standalone
    import table_arena  # type: ignore
    import table_gwent  # type: ignore
    from table_cards import GWENT_FACTIONS, GWENT_WEATHER  # type: ignore

WINNER_LABEL = {"player": "You win", "opponent": "Opponent wins", "draw": "Draw"}


def _winner(state: dict) -> str:
    return WINNER_LABEL.get(state.get("winner") or "", "")


def _turn_label(state: dict) -> str:
    if state.get("winner"):
        return _winner(state).lower()
    return "your move" if state["turn"] == "player" else "opponent's move"


def _gwent_row(state: dict, side: str, row: str) -> str:
    pile = state["sides"][side]
    cards = pile["rows"][row]
    body = " · ".join(f"{c['name']} {c['strength']}" for c in cards) or "—"
    horn = "  [HORN]" if pile["horns"].get(row) else ""
    return f"  {row:<7}▸ {body}{horn}   = {table_gwent.row_score(state, side, row)}"


def render_gwent(state: dict, reveal: bool = False) -> str:
    lines = [
        f"GWENT · round {state['round']}/3 · {_turn_label(state)}",
    ]
    for side in ("opponent", "player"):
        pile = state["sides"][side]
        faction = GWENT_FACTIONS.get(pile.get("faction"), side)
        who = "You" if side == "player" else "Opponent"
        lines.append("")
        lines.append(
            f"{who} · {faction} · score {table_gwent.score(state, side)} · "
            f"rounds {pile['won']} · hand {len(pile['hand'])} · deck {len(pile['deck'])}"
        )
        for row in table_gwent.GWENT_ROWS:
            lines.append(_gwent_row(state, side, row))
        if side == "opponent":
            if reveal:
                shown = " · ".join(c["name"] for c in pile["hand"]) or "—"
                lines.append(f"  hand    ▸ {shown}")
            else:
                lines.append(f"  hand    ▸ {len(pile['hand'])} hidden card(s)")
    weather = []
    for key in state["weather"]:
        name, row = GWENT_WEATHER.get(key, (key, ""))
        weather.append(f"{name} ({row})")
    lines.append("")
    lines.append(f"Weather: {' · '.join(weather) if weather else 'clear'}")
    lines.append(f"Rounds won: you {state['sides']['player']['won']} — "
                 f"opponent {state['sides']['opponent']['won']}")

    lines.append("")
    lines.append("HAND")
    hand = state["sides"]["player"]["hand"]
    if not hand:
        lines.append("  (empty)")
    for index, card in enumerate(hand, 1):
        kind = card.get("kind")
        if kind in ("unit", "hero"):
            tag = f"{card['row']} · {card['strength']}"
            if kind == "hero":
                tag += " · hero"
        elif kind == "spy":
            tag = f"spy · {card['strength']} · played to the enemy, draw 2"
        elif kind == "weather":
            tag = "weather · sets a row to 1"
        elif kind == "clear":
            tag = "special · remove all weather"
        elif kind == "horn":
            tag = "special · double a row (add row)"
        elif kind == "scorch":
            tag = "special · destroy the strongest non-hero units"
        else:
            tag = card.get("text", kind)
        lines.append(f"  [{index}] {card['name']} · {tag}")

    lines.append("")
    lines.append(table_gwent.legal_hint(state))
    return "\n".join(lines)


def _arena_status(minion: dict) -> str:
    flags = []
    if minion.get("taunt"):
        flags.append("taunt")
    if minion.get("shield"):
        flags.append("shield")
    if minion.get("charge"):
        flags.append("charge")
    if minion.get("sick"):
        flags.append("sick")
    if minion.get("attacked"):
        flags.append("done")
    return f" ({', '.join(flags)})" if flags else ""


def _arena_board(state: dict, side: str) -> str:
    board = state["sides"][side]["board"]
    if not board:
        return "  board   —"
    parts = []
    for index, minion in enumerate(board, 1):
        parts.append(
            f"[{index}] {minion['name']} "
            f"{minion['attack']}/{minion['health']}{_arena_status(minion)}"
        )
    return "  board   " + " · ".join(parts)


def render_arena(state: dict, reveal: bool = False) -> str:
    lines = [f"ARENA · turn {state['turn_no']} · {_turn_label(state)}"]
    for side in ("opponent", "player"):
        pile = state["sides"][side]
        who = "You" if side == "player" else "Opponent"
        lines.append("")
        lines.append(
            f"{who} · hero {pile['hero']}/30 · mana {pile['mana']}/{pile['max_mana']} · "
            f"hand {len(pile['hand'])} · deck {len(pile['deck'])}"
        )
        lines.append(_arena_board(state, side))
        if side == "opponent":
            if reveal:
                shown = ", ".join(c["name"] for c in pile["hand"]) or "—"
                lines.append(f"  hand    ▸ {shown}")
            else:
                lines.append(f"  hand    ▸ {len(pile['hand'])} hidden card(s)")
    lines.append("")
    if state["log"]:
        lines.append(f"last: {state['log'][-1]}")
    lines.append("")
    lines.append("HAND")
    hand = state["sides"]["player"]["hand"]
    if not hand:
        lines.append("  (empty)")
    for index, card in enumerate(hand, 1):
        if card["kind"] == "minion":
            flags = []
            if card.get("taunt"):
                flags.append("taunt")
            if card.get("charge"):
                flags.append("charge")
            if card.get("shield"):
                flags.append("shield")
            cry = card.get("battlecry")
            if cry:
                flags.append(f"battlecry: {cry['type']} {cry['amount']}")
            suffix = f" · {', '.join(flags)}" if flags else ""
            lines.append(
                f"  [{index}] {card['name']} · {card['cost']} mana · "
                f"{card['attack']}/{card['health']}{suffix}"
            )
        else:
            spell = card.get("spell") or {}
            lines.append(
                f"  [{index}] {card['name']} · {card['cost']} mana · "
                f"{spell.get('type', 'spell')} {spell.get('amount', '')}"
            )
    lines.append("")
    lines.append(table_arena.legal_hint(state))
    return "\n".join(lines)


def render(state: dict, reveal: bool = False) -> str:
    if state["mode"] == "gwent":
        return render_gwent(state, reveal=reveal)
    return render_arena(state, reveal=reveal)


def public_view(state: dict) -> dict:
    """Structured, JSON-safe view for the desktop UI.

    The opponent's hand and deck contents never cross this boundary; only their
    counts do. Player cards carry their 1-based index so the UI can post moves.
    """
    view: dict = {
        "mode": state["mode"],
        "game_id": state.get("game_id"),
        "turn": state.get("turn"),
        "winner": state.get("winner"),
        "log": (state.get("log") or [])[-8:],
    }
    sides: dict = {}
    for side in ("player", "opponent"):
        pile = state["sides"][side]
        entry: dict = {
            "label": "You" if side == "player" else "Opponent",
            "hand_count": len(pile["hand"]),
            "deck_count": len(pile["deck"]),
        }
        if side == "player":
            if state["mode"] == "gwent":
                entry["hand"] = [
                    {
                        "index": index,
                        "name": card["name"],
                        "kind": card.get("kind"),
                        "row": card.get("row"),
                        "strength": card.get("strength", 0),
                        "text": card.get("text", ""),
                    }
                    for index, card in enumerate(pile["hand"], 1)
                ]
            else:
                entry["hand"] = [
                    {
                        "index": index,
                        "name": card["name"],
                        "kind": card["kind"],
                        "cost": card["cost"],
                        "attack": card.get("attack", 0),
                        "health": card.get("health", 0),
                        "taunt": bool(card.get("taunt")),
                        "charge": bool(card.get("charge")),
                        "shield": bool(card.get("shield")),
                        "battlecry": card.get("battlecry"),
                        "spell": card.get("spell"),
                        "text": card.get("text", ""),
                    }
                    for index, card in enumerate(pile["hand"], 1)
                ]
        if state["mode"] == "gwent":
            entry.update(
                {
                    "faction": GWENT_FACTIONS.get(pile.get("faction"), ""),
                    "score": table_gwent.score(state, side),
                    "won": pile["won"],
                    "passed": pile["passed"],
                    "horns": {row: bool(pile["horns"].get(row)) for row in table_gwent.GWENT_ROWS},
                    "rows": {
                        row: [
                            {"name": card["name"], "strength": card.get("strength", 0),
                             "kind": card.get("kind")}
                            for card in pile["rows"][row]
                        ]
                        for row in table_gwent.GWENT_ROWS
                    },
                }
            )
        else:
            entry.update(
                {
                    "hero": pile["hero"],
                    "mana": pile["mana"],
                    "max_mana": pile["max_mana"],
                    "fatigue": pile["fatigue"],
                    "board": [
                        {
                            "index": index,
                            "name": minion["name"],
                            "attack": minion["attack"],
                            "health": minion["health"],
                            "max_health": minion.get("max_health", minion["health"]),
                            "taunt": bool(minion.get("taunt")),
                            "charge": bool(minion.get("charge")),
                            "shield": bool(minion.get("shield")),
                            "sick": bool(minion.get("sick")),
                            "attacked": bool(minion.get("attacked")),
                        }
                        for index, minion in enumerate(pile["board"], 1)
                    ],
                }
            )
        sides[side] = entry
    view["sides"] = sides
    if state["mode"] == "gwent":
        view["round"] = state["round"]
        view["weather"] = [
            {"key": key, "name": GWENT_WEATHER.get(key, (key, ""))[0],
             "row": GWENT_WEATHER.get(key, ("", ""))[1]}
            for key in state["weather"]
        ]
    else:
        view["turn_no"] = state["turn_no"]
    return view


def snapshot(state: dict) -> dict:
    """Tiny, hand-free view for the TUI widget. Never includes hidden cards."""
    base = {
        "mode": state["mode"],
        "game_id": state.get("game_id"),
        "turn": state.get("turn"),
        "winner": state.get("winner"),
        "last": (state.get("log") or [""])[-1],
    }
    player = state["sides"]["player"]
    opponent = state["sides"]["opponent"]
    if state["mode"] == "gwent":
        base.update(
            {
                "round": state["round"],
                "player": {
                    "score": table_gwent.score(state, "player"),
                    "hand": len(player["hand"]),
                    "deck": len(player["deck"]),
                    "won": player["won"],
                },
                "opponent": {
                    "score": table_gwent.score(state, "opponent"),
                    "hand": len(opponent["hand"]),
                    "deck": len(opponent["deck"]),
                    "won": opponent["won"],
                },
            }
        )
    else:
        base.update(
            {
                "turn_no": state["turn_no"],
                "player": {
                    "hero": player["hero"],
                    "mana": player["mana"],
                    "max_mana": player["max_mana"],
                    "hand": len(player["hand"]),
                    "deck": len(player["deck"]),
                    "board": len(player["board"]),
                },
                "opponent": {
                    "hero": opponent["hero"],
                    "mana": opponent["mana"],
                    "max_mana": opponent["max_mana"],
                    "hand": len(opponent["hand"]),
                    "deck": len(opponent["deck"]),
                    "board": len(opponent["board"]),
                },
            }
        )
    return base
