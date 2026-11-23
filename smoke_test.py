#!/usr/bin/env python3
"""Standalone smoke test: no Hermes, no plugin host, no network.

Plays both modes AI-vs-AI across seeds and asserts every match terminates.
Run: python3 smoke_test.py [--show]
"""

from __future__ import annotations

import sys

import table_arena
import table_cards
import table_engine
import table_gwent


def self_play(mode: str, seed: int, max_steps: int = 400) -> dict:
    state = table_engine.new_game(mode, seed)
    steps = 0
    while not state.get("winner") and steps < max_steps:
        if mode == "gwent":
            action = table_gwent.ai_action(state, state["turn"])
            state, _events = table_gwent.apply(state, action)
        else:
            table_arena.ai_take_turn(state, state["turn"])
        steps += 1
    assert state.get("winner"), f"{mode} seed {seed} did not finish in {max_steps} steps"
    return state


def main() -> int:
    for faction in table_cards.GWENT_POOLS:
        deck = table_cards.build_gwent_deck(faction)
        assert len(deck) == 22, (faction, len(deck))
    for name in table_cards.ARENA_POOLS:
        deck = table_cards.build_arena_deck(name)
        assert len(deck) == 20, (name, len(deck))

    if "--show" in sys.argv:
        print(table_engine.render_board(table_engine.new_game("gwent", seed=7)))
        print("\n" + "=" * 70 + "\n")
        print(table_engine.render_board(table_engine.new_game("arena", seed=7)))

    wins = {"player": 0, "opponent": 0, "draw": 0}
    for seed in range(1, 21):
        for mode in ("gwent", "arena"):
            state = self_play(mode, seed)
            wins[state["winner"]] += 1
            snap = table_engine.board_snapshot(state)
            assert "hand" in snap["player"]
            assert snap["opponent"].get("hand", 0) >= 0
    print(f"self-play ok: {wins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
