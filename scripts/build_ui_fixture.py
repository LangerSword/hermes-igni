#!/usr/bin/env python3
"""Build a UI fixture for the desktop-page harness (no live backend needed)."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import table_cards
import table_gwent
from table_render import public_view

ROOT = Path(__file__).resolve().parents[1]


def card(key: str) -> dict:
    for faction in table_cards.GWENT_POOLS:
        for item in table_cards.build_gwent_deck(faction):
            if item["key"] == key:
                return item
    raise KeyError(key)


def main() -> int:
    state = table_gwent.new_game(seed=7)
    state["game_id"] = "gwent-fixture"
    state["round"] = 2
    state["weather"] = ["frost"]
    state["turn"] = "player"
    state["starter"] = "player"
    state["sides"]["player"]["won"] = 0
    state["sides"]["opponent"]["won"] = 1
    for side in ("player", "opponent"):
        pile = state["sides"][side]
        for row in table_gwent.GWENT_ROWS:
            pile["rows"][row] = []
            pile["horns"][row] = False
        pile["hand"] = []
        pile["deck"] = []
        pile["passed"] = False

    player = state["sides"]["player"]
    opponent = state["sides"]["opponent"]
    player["rows"]["melee"] = [card("blue_stripes"), card("geralt")]
    player["rows"]["ranged"] = [card("philippa"), card("crinfrid_reavers")]
    player["rows"]["siege"] = [card("ballista"), card("catapult")]
    player["hand"] = [
        card("horn"),
        card("dijkstra"),
        card("frost"),
        card("clear"),
        card("scorch"),
        card("redanian_elite"),
        card("trebuchet"),
        card("poor_infantry"),
    ]
    player["deck"] = [card("aedirnian_mauler")] * 4

    opponent["rows"]["melee"] = [card("impera"), card("alba_pikemen")]
    opponent["rows"]["ranged"] = [card("black_archer"), card("tibor")]
    opponent["rows"]["siege"] = [card("mangonel"), card("menno")]
    opponent["hand"] = [card("etolian")] * 6
    opponent["deck"] = [card("scorpion")] * 5

    state["log"] = [
        "Round 2 begins — You lead.",
        "You play Blue Stripes Commando (4) to melee.",
        "Opponent plays Black Infantry Archer (6) to ranged.",
        "Weather: Biting Frost (melee).",
    ]

    view = public_view(state)
    keys = set()
    for item in view["sides"]["player"]["hand"]:
        keys.add(item["key"])
    for side in ("player", "opponent"):
        for row in table_gwent.GWENT_ROWS:
            for item in view["sides"][side]["rows"][row]:
                keys.add(item["key"])
    keys.add("card_back")

    art = {}
    for key in sorted(k for k in keys if k):
        stem = table_cards.ART_BY_KEY.get(key, table_cards.ART_BACK)
        path = ROOT / "art" / f"{stem}.webp"
        if path.is_file():
            art[key] = "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode("ascii")

    fixture = {"state": {"active": True, "view": view}, "art": art}
    out = ROOT / "test" / "ui-fixture.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(fixture), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024}KB, {len(art)} art keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
