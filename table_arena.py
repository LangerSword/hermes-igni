"""Arena: a compact mana duel with taunts, charge, shields and battlecries.

Deterministic per seed; the AI reads only its own hand and the public board.
"""

from __future__ import annotations

import random
from typing import Any

try:  # package import under Hermes
    from .table_cards import ARENA_DECKS, build_arena_deck
    from .table_common import GameError, SIDE_LABEL, other
except ImportError:  # standalone
    from table_cards import ARENA_DECKS, build_arena_deck  # type: ignore
    from table_common import GameError, SIDE_LABEL, other  # type: ignore

HERO_HEALTH = 30
MAX_MANA = 10
MAX_BOARD = 7
MAX_HAND = 10


# ------------------------------------------------------------- helpers ----


def _append_log(state: dict, text: str) -> None:
    state["log"].append(text)
    if len(state["log"]) > 240:
        del state["log"][:60]


def _check_win(state: dict, side: str) -> None:
    if state["sides"][side]["hero"] <= 0:
        state["winner"] = other(side)
        state["turn"] = "over"
        _append_log(state, f"{SIDE_LABEL[side]} fall. {state['winner']} wins the duel.")


def _draw(state: dict, side: str, count: int = 1) -> int:
    pile = state["sides"][side]
    drawn = 0
    for _ in range(count):
        if state.get("winner"):
            break
        if not pile["deck"]:
            pile["fatigue"] += 1
            pile["hero"] -= pile["fatigue"]
            _append_log(
                state,
                f"{SIDE_LABEL[side]} draw from an empty deck: fatigue {pile['fatigue']}.",
            )
            _check_win(state, side)
            continue
        card = pile["deck"].pop(0)
        if len(pile["hand"]) >= MAX_HAND:
            _append_log(state, f"{SIDE_LABEL[side]} burn {card['name']} (hand full).")
            continue
        pile["hand"].append(card)
        drawn += 1
    return drawn


def _damage_minion(state: dict, side: str, minion: dict, amount: int) -> None:
    if amount <= 0:
        return
    if minion.get("shield"):
        minion["shield"] = False
        _append_log(state, f"{minion['name']}'s shield absorbs the hit.")
        return
    minion["health"] = int(minion["health"]) - int(amount)


def _damage_hero(state: dict, side: str, amount: int) -> None:
    if amount <= 0:
        return
    state["sides"][side]["hero"] -= int(amount)
    _check_win(state, side)


def _reap(state: dict, side: str) -> None:
    pile = state["sides"][side]
    alive = []
    for minion in pile["board"]:
        if int(minion["health"]) <= 0:
            pile["discard"].append(minion)
            _append_log(state, f"{minion['name']} dies.")
        else:
            alive.append(minion)
    pile["board"] = alive


def _find_target(state: dict, side: str, target: Any):
    """Resolve a target into ('hero', None) or ('minion', card)."""
    enemy = state["sides"][other(side)]
    if target in (None, "", "hero", "face"):
        return "hero", None
    try:
        index = int(target)
    except (TypeError, ValueError):
        raise GameError("target must be 'hero' or a 1-based enemy board index.")
    if not 1 <= index <= len(enemy["board"]):
        raise GameError(
            f"target {index} is out of range; the enemy board has {len(enemy['board'])} minion(s)."
        )
    return "minion", enemy["board"][index - 1]


def _taunt_guard(state: dict, side: str, target: Any) -> None:
    enemy = state["sides"][other(side)]
    taunts = [m for m in enemy["board"] if m.get("taunt")]
    if not taunts:
        return
    if target in (None, "", "hero", "face"):
        names = ", ".join(f"[{enemy['board'].index(m) + 1}] {m['name']}" for m in taunts)
        raise GameError(f"a taunt minion must be attacked first: {names}.")
    try:
        index = int(target)
    except (TypeError, ValueError):
        return
    if not 1 <= index <= len(enemy["board"]):
        return  # out-of-range is reported by _find_target
    if not enemy["board"][index - 1].get("taunt"):
        names = ", ".join(f"[{enemy['board'].index(m) + 1}] {m['name']}" for m in taunts)
        raise GameError(f"a taunt minion must be attacked first: {names}.")


# --------------------------------------------------------------- setup ----


def new_game(
    seed: int | None = None,
    player_deck: str = "vanguard",
    ai_deck: str = "syndicate",
) -> dict:
    seed = int(seed if seed is not None else random.randrange(1, 10**9))
    rng = random.Random(seed)
    state: dict[str, Any] = {
        "mode": "arena",
        "game_id": f"arena-{seed}",
        "seed": seed,
        "turn": "player",
        "turn_no": 0,
        "winner": None,
        "log": [],
        "sides": {},
    }
    initial = {"player": 3, "opponent": 4}
    for side, deck_name in (("player", player_deck), ("opponent", ai_deck)):
        deck = build_arena_deck(deck_name)
        rng.shuffle(deck)
        for index, card in enumerate(deck):
            card["uid"] = f"{side[0]}{index}"
            card["max_health"] = card.get("health", 0)
        state["sides"][side] = {
            "deck_name": deck_name,
            "hero": HERO_HEALTH,
            "mana": 0,
            "max_mana": 0,
            "hand": deck[: initial[side]],
            "deck": deck[initial[side] :],
            "board": [],
            "discard": [],
            "fatigue": 0,
        }
    _begin_turn(state, "player")
    _append_log(
        state,
        f"{ARENA_DECKS[player_deck]} vs {ARENA_DECKS[ai_deck]} — you lead.",
    )
    return state


def _begin_turn(state: dict, side: str) -> None:
    pile = state["sides"][side]
    pile["max_mana"] = min(MAX_MANA, pile["max_mana"] + 1)
    pile["mana"] = pile["max_mana"]
    for minion in pile["board"]:
        minion["sick"] = False
        minion["attacked"] = False
    _draw(state, side, 1)
    if not state.get("winner"):
        state["turn"] = side
        state["turn_no"] += 1


def _finish_turn(state: dict, side: str) -> None:
    if state.get("winner"):
        return
    _begin_turn(state, other(side))


# ------------------------------------------------------------- effects ----


def _battlecry(state: dict, side: str, minion: dict) -> None:
    cry = minion.get("battlecry")
    if not cry:
        return
    kind = cry.get("type")
    amount = int(cry.get("amount", 1))
    if kind == "draw":
        _draw(state, side, amount)
        _append_log(state, f"{minion['name']} draws {amount}.")
    elif kind == "aoe":
        enemy = state["sides"][other(side)]
        for target in list(enemy["board"]):
            _damage_minion(state, other(side), target, amount)
        _reap(state, other(side))
        _append_log(state, f"{minion['name']} deals {amount} to all enemy minions.")
    elif kind == "heal":
        pile = state["sides"][side]
        pile["hero"] = min(HERO_HEALTH, pile["hero"] + amount)
        _append_log(state, f"{minion['name']} restores {amount} health.")


def _cast_spell(state: dict, side: str, card: dict, target: Any) -> None:
    spell = card.get("spell") or {}
    kind = spell.get("type")
    amount = int(spell.get("amount", 1))
    if kind == "damage":
        if target in (None, ""):
            raise GameError(
                f"{card['name']} needs a target: 'hero' or an enemy board index."
            )
        kind_t, ref = _find_target(state, side, target)
        if kind_t == "hero":
            _damage_hero(state, other(side), amount)
            _append_log(state, f"{card['name']} hits the enemy hero for {amount}.")
        else:
            _damage_minion(state, other(side), ref, amount)
            _append_log(state, f"{card['name']} hits {ref['name']} for {amount}.")
            _reap(state, other(side))
    elif kind == "draw":
        _draw(state, side, amount)
        _append_log(state, f"{card['name']} draws {amount}.")
    elif kind == "heal":
        pile = state["sides"][side]
        healed = min(HERO_HEALTH, pile["hero"] + amount) - pile["hero"]
        pile["hero"] += healed
        _append_log(state, f"{card['name']} restores {healed} health.")
    elif kind == "aoe":
        enemy = state["sides"][other(side)]
        for target_card in list(enemy["board"]):
            _damage_minion(state, other(side), target_card, amount)
        _reap(state, other(side))
        _append_log(state, f"{card['name']} deals {amount} to all enemy minions.")
    else:
        raise GameError(f"{card['name']} has no implemented effect.")


def _play_card(state: dict, side: str, action: dict) -> None:
    hand = state["sides"][side]["hand"]
    try:
        index = int(action.get("card", 0))
    except (TypeError, ValueError):
        raise GameError("card must be the 1-based number of a card in hand.")
    if not 1 <= index <= len(hand):
        raise GameError(
            f"card {index} is out of range; your hand has {len(hand)} card(s) (1-{len(hand)})."
            if hand
            else "your hand is empty — end the turn."
        )
    card = hand[index - 1]
    pile = state["sides"][side]
    if card["cost"] > pile["mana"]:
        raise GameError(
            f"{card['name']} costs {card['cost']} mana; you have {pile['mana']}."
        )
    if card["kind"] == "minion" and len(pile["board"]) >= MAX_BOARD:
        raise GameError("your board is full (7 minions); attack or end the turn.")

    # Validate spell targets before paying mana.
    if card["kind"] == "spell" and (card.get("spell") or {}).get("type") == "damage":
        target = action.get("target")
        if target in (None, ""):
            raise GameError(
                f"{card['name']} needs a target: 'hero' or an enemy board index."
            )
        kind_t, ref = _find_target(state, side, target)
        if kind_t == "minion" and ref not in state["sides"][other(side)]["board"]:
            raise GameError("that target is no longer on the board.")

    pile["mana"] -= card["cost"]
    hand.pop(index - 1)

    if card["kind"] == "minion":
        card["health"] = int(card.get("max_health", card.get("health", 1)))
        card["sick"] = not card.get("charge", False)
        card["attacked"] = False
        pile["board"].append(card)
        _append_log(
            state,
            f"{SIDE_LABEL[side]} summon {card['name']} "
            f"({card['attack']}/{card['health']}"
            f"{', taunt' if card.get('taunt') else ''}"
            f"{', charge' if card.get('charge') else ''}).",
        )
        _battlecry(state, side, card)
    else:
        _cast_spell(state, side, card, action.get("target"))
        pile["discard"].append(card)
        _append_log(state, f"{SIDE_LABEL[side]} cast {card['name']}.")


def _attack(state: dict, side: str, action: dict) -> None:
    pile = state["sides"][side]
    try:
        index = int(action.get("attacker", 0))
    except (TypeError, ValueError):
        raise GameError("attacker must be the 1-based index of one of your minions.")
    if not 1 <= index <= len(pile["board"]):
        raise GameError(
            f"attacker {index} is out of range; your board has {len(pile['board'])} minion(s)."
        )
    attacker = pile["board"][index - 1]
    if attacker.get("sick"):
        raise GameError(f"{attacker['name']} just arrived and cannot attack this turn.")
    if attacker.get("attacked"):
        raise GameError(f"{attacker['name']} has already attacked this turn.")
    if int(attacker.get("attack", 0)) <= 0:
        raise GameError(f"{attacker['name']} has no attack.")
    target = action.get("target", "hero")
    _taunt_guard(state, side, target)
    kind_t, ref = _find_target(state, side, target)
    attacker["attacked"] = True
    if kind_t == "hero":
        _damage_hero(state, other(side), int(attacker["attack"]))
        _append_log(
            state,
            f"{attacker['name']} hits the enemy hero for {attacker['attack']}.",
        )
        return
    _append_log(
        state,
        f"{attacker['name']} ({attacker['attack']}/{attacker['health']}) attacks "
        f"{ref['name']} ({ref['attack']}/{ref['health']}).",
    )
    _damage_minion(state, other(side), ref, int(attacker["attack"]))
    _damage_minion(state, side, attacker, int(ref["attack"]))
    _reap(state, other(side))
    _reap(state, side)


# ---------------------------------------------------------------- apply ----


def _apply_core(state: dict, side: str, action: dict) -> None:
    if state.get("winner"):
        raise GameError(f"the duel is over ({state['winner']}); start a new table.")
    if state["turn"] != side:
        raise GameError(f"it is {state['turn']}'s turn, not {side}'s.")
    move = str(action.get("action", "")).strip().lower()
    if move == "concede":
        state["winner"] = other(side)
        state["turn"] = "over"
        _append_log(state, f"{SIDE_LABEL[side]} concede. {state['winner']} wins.")
        return
    if move == "play":
        _play_card(state, side, action)
        return
    if move == "attack":
        _attack(state, side, action)
        return
    if move == "end_turn":
        _finish_turn(state, side)
        return
    raise GameError(
        "action must be 'play', 'attack', 'end_turn' or 'concede' in Arena."
    )


def apply(state: dict, action: dict) -> tuple[dict, list[str]]:
    before = len(state["log"])
    side = state["turn"]
    _apply_core(state, side, action)
    if state.get("winner"):
        return state, state["log"][before:]
    if str(action.get("action", "")).lower() == "end_turn":
        # The opponent takes its whole turn immediately: a chat turn should not
        # end with "your move" while the AI is still holding cards.
        ai_take_turn(state, "opponent")
    return state, state["log"][before:]


# ------------------------------------------------------------------- AI ----


def _available_attackers(pile: dict) -> list[dict]:
    return [
        m
        for m in pile["board"]
        if not m.get("sick") and not m.get("attacked") and int(m.get("attack", 0)) > 0
    ]


def _minion_value(minion: dict) -> float:
    value = float(minion.get("attack", 0) + minion.get("health", 0))
    if minion.get("taunt"):
        value += 1.5
    if minion.get("shield"):
        value += 1.5
    return value


def _best_play(state: dict, side: str) -> dict | None:
    pile = state["sides"][side]
    enemy = state["sides"][other(side)]
    board_full = len(pile["board"]) >= MAX_BOARD
    options: list[tuple[float, int, dict]] = []

    for index, card in enumerate(pile["hand"], 1):
        if card["cost"] > pile["mana"]:
            continue
        if card["kind"] == "minion":
            if board_full:
                continue
            value = float(card["attack"] + card["health"])
            if card.get("taunt"):
                value += 1.5
            if card.get("charge"):
                value += 2
            if card.get("shield"):
                value += 1.5
            cry = card.get("battlecry") or {}
            if cry.get("type") == "draw":
                value += 2
            elif cry.get("type") == "aoe":
                value += 2 * sum(
                    1 for m in enemy["board"] if m.get("health", 0) <= cry.get("amount", 1)
                )
            options.append((value, card["cost"], {"action": "play", "card": index}))
            continue

        spell = card.get("spell") or {}
        kind = spell.get("type")
        amount = int(spell.get("amount", 0))
        if kind == "damage":
            if enemy["hero"] <= amount:
                options.append(
                    (100.0, card["cost"], {"action": "play", "card": index, "target": "hero"})
                )
                continue
            killable = [
                m for m in enemy["board"] if int(m.get("health", 0)) <= amount
            ]
            if killable:
                best = max(killable, key=_minion_value)
                value = _minion_value(best) + 2
                options.append(
                    (
                        value,
                        card["cost"],
                        {
                            "action": "play",
                            "card": index,
                            "target": str(enemy["board"].index(best) + 1),
                        },
                    )
                )
            elif amount >= 3:
                options.append(
                    (1.5, card["cost"], {"action": "play", "card": index, "target": "hero"})
                )
        elif kind == "aoe":
            hits = [m for m in enemy["board"] if int(m.get("health", 0)) <= amount]
            if hits:
                value = sum(_minion_value(m) for m in hits)
                options.append((value, card["cost"], {"action": "play", "card": index}))
        elif kind == "draw":
            if len(pile["hand"]) <= 7:
                options.append((2.5, card["cost"], {"action": "play", "card": index}))
        elif kind == "heal":
            if pile["hero"] <= 22:
                options.append((2.0, card["cost"], {"action": "play", "card": index}))

    if not options:
        return None
    options.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return options[0][2]


def _best_attack(state: dict, side: str) -> dict | None:
    pile = state["sides"][side]
    enemy = state["sides"][other(side)]
    attackers = _available_attackers(pile)
    if not attackers:
        return None
    taunts = [m for m in enemy["board"] if m.get("taunt")]
    targets = taunts if taunts else enemy["board"]

    if not taunts and sum(int(a["attack"]) for a in attackers) >= enemy["hero"]:
        return {
            "action": "attack",
            "attacker": pile["board"].index(attackers[0]) + 1,
            "target": "hero",
        }

    best: tuple[float, dict] | None = None
    for attacker in attackers:
        for target in targets:
            damage = int(attacker["attack"])
            kill = damage >= int(target["health"])
            value = _minion_value(target) if kill else 0.0
            # A trade that kills our minion is worth less.
            if int(target["attack"]) >= int(attacker["health"]):
                value -= _minion_value(attacker) / 2
            if kill and value > 0:
                action = {
                    "action": "attack",
                    "attacker": pile["board"].index(attacker) + 1,
                    "target": str(enemy["board"].index(target) + 1),
                }
                if best is None or value > best[0]:
                    best = (value, action)
    if best is not None:
        return best[1]
    if taunts:
        # Nothing good to trade into: chip the smallest taunt.
        target = min(taunts, key=lambda m: (m["health"], m["attack"]))
        return {
            "action": "attack",
            "attacker": pile["board"].index(attackers[0]) + 1,
            "target": str(enemy["board"].index(target) + 1),
        }
    attacker = max(attackers, key=lambda m: int(m["attack"]))
    return {
        "action": "attack",
        "attacker": pile["board"].index(attacker) + 1,
        "target": "hero",
    }


def _choose_action(state: dict, side: str) -> dict | None:
    play = _best_play(state, side)
    if play is not None:
        return play
    return _best_attack(state, side)


def ai_take_turn(state: dict, side: str) -> None:
    guard = 0
    while not state.get("winner") and guard < 80:
        action = _choose_action(state, side)
        if action is None:
            break
        _apply_core(state, side, action)
        guard += 1
    if not state.get("winner"):
        _finish_turn(state, side)


# --------------------------------------------------------------- hints ----


def legal_hint(state: dict) -> str:
    if state.get("winner"):
        return f"Duel over: {state['winner']}. Start a new table with table_new."
    if state["turn"] != "player":
        return "Opponent to move."
    return (
        "Your move: play <hand#> [target] · attack <your board#> <enemy board#|hero> · "
        "end_turn."
    )
