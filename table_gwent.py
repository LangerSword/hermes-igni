"""Gwent-style row warfare: weather, spies, horns, scorch, best of three.

The engine is deterministic for a given seed and owns all hidden information.
The AI only reads its own hand and the public board, never the player's hand.
"""

from __future__ import annotations

import copy
import random
from typing import Any

try:  # package import under Hermes
    from .table_cards import (
        GWENT_FACTIONS,
        GWENT_ROWS,
        GWENT_WEATHER,
        build_gwent_deck,
    )
    from .table_common import GameError, SIDE_LABEL, other
except ImportError:  # standalone: python -m unittest / CLI
    from table_cards import (  # type: ignore
        GWENT_FACTIONS,
        GWENT_ROWS,
        GWENT_WEATHER,
        build_gwent_deck,
    )
    from table_common import GameError, SIDE_LABEL, other  # type: ignore

INITIAL_HAND = 10
ROUNDS_TO_WIN = 2


# ------------------------------------------------------------- helpers ----


def _append_log(state: dict, text: str) -> None:
    state["log"].append(text)
    if len(state["log"]) > 240:
        del state["log"][:60]


def _draw(state: dict, side: str, count: int) -> int:
    pile = state["sides"][side]
    drawn = 0
    for _ in range(count):
        if not pile["deck"]:
            break
        if len(pile["hand"]) >= 12:
            pile["deck"].pop(0)
            continue
        pile["hand"].append(pile["deck"].pop(0))
        drawn += 1
    return drawn


def _weather_row(state: dict, row: str) -> bool:
    for key in state["weather"]:
        if GWENT_WEATHER.get(key, ("", ""))[1] == row:
            return True
    return False


def _effective(card: dict, state: dict, row: str) -> int:
    if card.get("kind") == "hero":
        return int(card.get("strength", 0))
    if _weather_row(state, row):
        return 1
    return int(card.get("strength", 0))


def row_score(state: dict, side: str, row: str) -> int:
    pile = state["sides"][side]
    total = sum(_effective(card, state, row) for card in pile["rows"][row])
    if pile["horns"].get(row):
        total *= 2
    return total


def score(state: dict, side: str) -> int:
    return sum(row_score(state, side, row) for row in GWENT_ROWS)


def _cards_on_board(state: dict):
    for side in ("player", "opponent"):
        for row in GWENT_ROWS:
            for card in state["sides"][side]["rows"][row]:
                yield side, row, card


# --------------------------------------------------------------- setup ----


def new_game(
    seed: int | None = None,
    player_faction: str = "northern",
    ai_faction: str = "nilfgaard",
) -> dict:
    seed = int(seed if seed is not None else random.randrange(1, 10**9))
    rng = random.Random(seed)
    state: dict[str, Any] = {
        "mode": "gwent",
        "game_id": f"gwent-{seed}",
        "seed": seed,
        "round": 1,
        "turn": "player",
        "starter": "player",
        "weather": [],
        "winner": None,
        "log": [],
        "sides": {},
    }
    for side, faction in (("player", player_faction), ("opponent", ai_faction)):
        deck = build_gwent_deck(faction)
        rng.shuffle(deck)
        for index, card in enumerate(deck):
            card["uid"] = f"{side[0]}{index}"
        state["sides"][side] = {
            "faction": faction,
            "hand": deck[:INITIAL_HAND],
            "deck": deck[INITIAL_HAND:],
            "discard": [],
            "rows": {row: [] for row in GWENT_ROWS},
            "horns": {row: False for row in GWENT_ROWS},
            "passed": False,
            "won": 0,
        }
    _append_log(
        state,
        f"{GWENT_FACTIONS[player_faction]} vs {GWENT_FACTIONS[ai_faction]} — "
        "best of three. You lead.",
    )
    return state


def _side_name(state: dict, side: str) -> str:
    faction = state["sides"][side].get("faction", "")
    return GWENT_FACTIONS.get(faction, SIDE_LABEL[side])


# ---------------------------------------------------------- card effects ----


def _destroy_strongest(state: dict) -> None:
    best = 0
    for _side, _row, card in _cards_on_board(state):
        if card.get("kind") != "hero":
            best = max(best, int(card.get("strength", 0)))
    if best <= 0:
        _append_log(state, "Scorch finds nothing.")
        return
    destroyed: list[str] = []
    for side in ("player", "opponent"):
        for row in GWENT_ROWS:
            keep = []
            for card in state["sides"][side]["rows"][row]:
                if card.get("kind") != "hero" and int(card.get("strength", 0)) == best:
                    state["sides"][side]["discard"].append(card)
                    destroyed.append(card["name"])
                else:
                    keep.append(card)
            state["sides"][side]["rows"][row] = keep
    if destroyed:
        _append_log(
            state,
            f"Scorch destroys {', '.join(destroyed)} ({best} strength).",
        )
    else:
        _append_log(state, "Scorch finds nothing.")


def _execute_card(
    state: dict, side: str, card: dict, row: str | None = None, log: bool = True
) -> None:
    kind = card.get("kind", "unit")
    name = card["name"]
    prefix = SIDE_LABEL[side]
    if kind == "weather":
        if card["key"] not in state["weather"]:
            state["weather"].append(card["key"])
        if log:
            _append_log(state, f"{prefix} play {name}. Weather changes.")
        return
    if kind == "clear":
        state["weather"] = []
        if log:
            _append_log(state, f"{prefix} play {name}. Skies clear.")
        return
    if kind == "horn":
        if row not in GWENT_ROWS:
            raise GameError(
                "Commander's Horn needs a row: melee, ranged or siege."
            )
        state["sides"][side]["horns"][row] = True
        if log:
            _append_log(state, f"{prefix} sound the Horn on {row}.")
        return
    if kind == "scorch":
        if log:
            _append_log(state, f"{prefix} play Scorch.")
        _destroy_strongest(state)
        return
    if kind == "spy":
        target = state["sides"][other(side)]
        target["rows"][card["row"]].append(card)
        drawn = _draw(state, side, 2)
        if log:
            _append_log(
                state,
                f"{prefix} send {name} ({card['strength']}) to the enemy row and draw {drawn}.",
            )
        return
    state["sides"][side]["rows"][card["row"]].append(card)
    if log:
        _append_log(
            state,
            f"{prefix} play {name} ({card['strength']}) to {card['row']}.",
        )


def _play(state: dict, side: str, action: dict) -> None:
    hand = state["sides"][side]["hand"]
    try:
        index = int(action.get("card", 0))
    except (TypeError, ValueError):
        raise GameError("card must be the 1-based number of a card in hand.")
    if not 1 <= index <= len(hand):
        raise GameError(
            f"card {index} is out of range; your hand has {len(hand)} card(s) (1-{len(hand)})."
            if hand
            else "your hand is empty — pass or concede."
        )
    card = hand.pop(index - 1)
    row = action.get("row")
    if card.get("kind") == "horn" and not row:
        raise GameError("Commander's Horn needs a row: melee, ranged or siege.")
    _execute_card(state, side, card, row=row)
    if card.get("kind") in ("weather", "clear", "horn", "scorch"):
        state["sides"][side]["discard"].append(card)


def _resolve_round(state: dict) -> None:
    player_score = score(state, "player")
    opponent_score = score(state, "opponent")
    if player_score > opponent_score:
        state["sides"]["player"]["won"] += 1
        winner = "player"
        _append_log(
            state,
            f"Round {state['round']}: you take it {player_score}-{opponent_score}.",
        )
    elif opponent_score > player_score:
        state["sides"]["opponent"]["won"] += 1
        winner = "opponent"
        _append_log(
            state,
            f"Round {state['round']}: opponent takes it {opponent_score}-{player_score}.",
        )
    else:
        state["sides"]["player"]["won"] += 1
        state["sides"]["opponent"]["won"] += 1
        winner = None
        _append_log(
            state,
            f"Round {state['round']}: tied {player_score}-{player_score}; both sides claim it.",
        )

    player_won = state["sides"]["player"]["won"]
    opponent_won = state["sides"]["opponent"]["won"]
    if player_won >= ROUNDS_TO_WIN or opponent_won >= ROUNDS_TO_WIN:
        if player_won > opponent_won:
            state["winner"] = "player"
        elif opponent_won > player_won:
            state["winner"] = "opponent"
        else:
            state["winner"] = "draw"
        state["turn"] = "over"
        _append_log(state, f"Match over — {state['winner']}.")
        return

    state["round"] += 1
    previous_starter = state["starter"]
    state["starter"] = winner if winner else other(previous_starter)
    state["turn"] = state["starter"]
    for side in ("player", "opponent"):
        pile = state["sides"][side]
        for row in GWENT_ROWS:
            pile["discard"].extend(pile["rows"][row])
            pile["rows"][row] = []
            pile["horns"][row] = False
        pile["passed"] = False
    state["weather"] = []
    _append_log(
        state,
        f"Round {state['round']} begins — {SIDE_LABEL[state['turn']]} lead.",
    )


# ---------------------------------------------------------------- apply ----


def apply(state: dict, action: dict) -> tuple[dict, list[str]]:
    if state.get("winner"):
        raise GameError(
            f"the match is over ({state['winner']}); start a new table with table_new."
        )
    side = state["turn"]
    before = len(state["log"])
    move = str(action.get("action", "")).strip().lower()

    if move == "concede":
        state["winner"] = other(side)
        state["turn"] = "over"
        _append_log(state, f"{SIDE_LABEL[side]} concede. {state['winner']} wins.")
        return state, state["log"][before:]

    if move == "pass":
        pile = state["sides"][side]
        if pile["passed"]:
            raise GameError("that side has already passed this round.")
        pile["passed"] = True
        _append_log(state, f"{SIDE_LABEL[side]} pass.")
        if all(state["sides"][s]["passed"] for s in ("player", "opponent")):
            _resolve_round(state)
        else:
            state["turn"] = other(side)
        return state, state["log"][before:]

    if move != "play":
        raise GameError(
            "action must be 'play', 'pass' or 'concede' in Gwent."
        )

    _play(state, side, action)

    if state["sides"]["player"]["passed"] and state["sides"]["opponent"]["passed"]:
        _resolve_round(state)
        return state, state["log"][before:]

    nxt = other(side)
    if state["sides"][nxt]["passed"]:
        nxt = side
    state["turn"] = nxt
    return state, state["log"][before:]


# ------------------------------------------------------------------- AI ----


def _preview_scores(
    state: dict, side: str, card: dict, row: str | None
) -> tuple[int, int]:
    sim = copy.deepcopy(state)
    sim["sides"][side]["hand"] = [
        c for c in sim["sides"][side]["hand"] if c.get("uid") != card.get("uid")
    ]
    _execute_card(sim, side, card, row=row, log=False)
    return score(sim, side), score(sim, other(side))


def _horn_row(state: dict, side: str) -> str:
    best_row = max(GWENT_ROWS, key=lambda r: row_score(state, side, r))
    return best_row


def _candidate(
    state: dict, side: str, card: dict
) -> tuple[int, int, str | None]:
    row = None
    if card.get("kind") == "horn":
        row = _horn_row(state, side)
    me_before = score(state, side)
    you_before = score(state, other(side))
    me_after, you_after = _preview_scores(state, side, card, row)
    swing = (me_after - me_before) - (you_after - you_before)
    if card.get("kind") == "spy":
        swing += 6  # two cards are worth roughly six strength here
    return swing, me_after - you_after, row


def ai_action(state: dict, side: str = "opponent") -> dict:
    """Choose one legal action for *side* using only public information."""
    hand = state["sides"][side]["hand"]
    if not hand:
        return {"action": "pass"}
    me = score(state, side)
    you = score(state, other(side))
    opponent_passed = state["sides"][other(side)]["passed"]

    candidates = []
    for index, card in enumerate(hand, 1):
        swing, lead_after, row = _candidate(state, side, card)
        candidates.append(
            {
                "index": index,
                "card": card,
                "swing": swing,
                "lead_after": lead_after,
                "row": row,
            }
        )

    if opponent_passed:
        if me > you:
            return {"action": "pass"}
        overtakes = [
            c for c in candidates if c["lead_after"] > 0
        ]
        if overtakes:
            pick = min(overtakes, key=lambda c: c["swing"])
            action = {"action": "play", "card": pick["index"]}
            if pick["row"]:
                action["row"] = pick["row"]
            return action
        pick = max(candidates, key=lambda c: c["swing"])
        if pick["swing"] <= 0:
            return {"action": "pass"}
        action = {"action": "play", "card": pick["index"]}
        if pick["row"]:
            action["row"] = pick["row"]
        return action

    # Both still holding cards: bank a big lead when the trade is even.
    if me - you >= 12 and len(hand) <= len(state["sides"][other(side)]["hand"]):
        return {"action": "pass"}

    pick = max(candidates, key=lambda c: (c["swing"], -c["index"]))
    if pick["swing"] <= 0:
        return {"action": "pass"}
    action = {"action": "play", "card": pick["index"]}
    if pick["row"]:
        action["row"] = pick["row"]
    return action


# --------------------------------------------------------------- hints ----


def legal_hint(state: dict) -> str:
    if state.get("winner"):
        return f"Match over: {state['winner']}. Start a new table with table_new."
    if state["turn"] != "player":
        return "Opponent to move."
    if state["sides"]["player"]["passed"]:
        return "You have passed this round; the opponent keeps playing until they pass."
    return "Your move: play <hand#> [row] for a horn, or pass."
