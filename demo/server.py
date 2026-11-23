"""Demo backend: the real Igni API plus a static harness, on one origin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["TABLE_DATA_DIR"] = str(ROOT / "demo" / ".state")
os.environ["TABLE_HOME"] = str(ROOT / "demo" / ".home")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dashboard"))

import table_cards  # noqa: E402
import table_gwent  # noqa: E402
import table_store  # noqa: E402
import plugin_api  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402


def card(key: str) -> dict:
    for faction in table_cards.GWENT_POOLS:
        for item in table_cards.build_gwent_deck(faction):
            if item["key"] == key:
                return item
    raise KeyError(key)


def demo_state() -> dict:
    state = table_gwent.new_game(seed=42)
    state["game_id"] = "igni-demo"
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
        card("dijkstra"),
        card("horn"),
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
        "Round 2 begins. You lead.",
        "Blue Stripes Commando takes the melee row.",
        "Black Infantry Archer answers in ranged.",
        "Biting Frost covers the melee row.",
    ]
    return state


def build_app() -> FastAPI:
    table_store.save(demo_state())
    app = FastAPI(title="Igni demo")
    app.include_router(plugin_api.router, prefix="/api/plugins/igni")
    app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="static")
    return app


app = build_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8124, log_level="warning")
