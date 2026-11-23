"""Behaviour tests for both engines, the tools and the hidden-information boundary.

Run: python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

# Isolate every path before importing the store.
_TMP = Path(tempfile.mkdtemp(prefix="hermes-table-tests-"))
os.environ["TABLE_DATA_DIR"] = str(_TMP / "data")
os.environ["TABLE_HOME"] = str(_TMP / "home")

import table_arena  # noqa: E402
import table_cards  # noqa: E402
import table_engine  # noqa: E402
import table_gwent  # noqa: E402
import table_render  # noqa: E402
import table_store  # noqa: E402
from table_common import GameError  # noqa: E402


def gwent_card(key: str) -> dict:
    for card in table_cards.build_gwent_deck("northern") + table_cards.build_gwent_deck(
        "nilfgaard"
    ):
        if card["key"] == key:
            return copy.deepcopy(card)
    raise KeyError(key)


def arena_card(key: str) -> dict:
    for deck in table_cards.ARENA_POOLS:
        for card in table_cards.build_arena_deck(deck):
            if card["key"] == key:
                card = copy.deepcopy(card)
                card["max_health"] = card.get("health", 0)
                return card
    raise KeyError(key)


def blank_gwent(seed: int = 1) -> dict:
    state = table_gwent.new_game(seed=seed)
    for side in ("player", "opponent"):
        pile = state["sides"][side]
        pile["hand"] = []
        pile["deck"] = []
        for row in table_gwent.GWENT_ROWS:
            pile["rows"][row] = []
            pile["horns"][row] = False
    state["weather"] = []
    state["turn"] = "player"
    return state


class DeckTests(unittest.TestCase):
    def test_gwent_decks_are_22(self):
        for faction in table_cards.GWENT_POOLS:
            self.assertEqual(len(table_cards.build_gwent_deck(faction)), 22)

    def test_arena_decks_are_20(self):
        for deck in table_cards.ARENA_POOLS:
            self.assertEqual(len(table_cards.build_arena_deck(deck)), 20)

    def test_initial_hands(self):
        gwent = table_gwent.new_game(seed=3)
        self.assertEqual(len(gwent["sides"]["player"]["hand"]), 10)
        self.assertEqual(len(gwent["sides"]["opponent"]["hand"]), 10)
        arena = table_arena.new_game(seed=3)
        self.assertEqual(len(arena["sides"]["player"]["hand"]), 4)
        self.assertEqual(len(arena["sides"]["opponent"]["hand"]), 4)
        self.assertEqual(arena["sides"]["player"]["mana"], 1)


class GwentTests(unittest.TestCase):
    def test_weather_and_horn_scoring(self):
        state = blank_gwent()
        melee = gwent_card("blue_stripes")  # 4, non-hero
        hero = gwent_card("geralt")  # 15, hero
        state["sides"]["player"]["rows"]["melee"] = [melee, hero]
        self.assertEqual(table_gwent.row_score(state, "player", "melee"), 4 + 15)
        state["weather"] = ["frost"]
        self.assertEqual(table_gwent.row_score(state, "player", "melee"), 1 + 15)
        state["sides"]["player"]["horns"]["melee"] = True
        self.assertEqual(table_gwent.row_score(state, "player", "melee"), (1 + 15) * 2)

    def test_spy_joins_enemy_and_draws_two(self):
        state = blank_gwent()
        spy = gwent_card("dijkstra")
        state["sides"]["player"]["hand"] = [spy]
        state["sides"]["player"]["deck"] = [gwent_card("ballista"), gwent_card("catapult")]
        state, _events = table_gwent.apply(state, {"action": "play", "card": 1})
        self.assertEqual(len(state["sides"]["player"]["hand"]), 2)
        self.assertEqual(len(state["sides"]["opponent"]["rows"]["melee"]), 1)
        self.assertEqual(state["sides"]["opponent"]["rows"]["melee"][0]["name"], spy["name"])

    def test_round_tie_awards_both_and_can_draw_match(self):
        state = blank_gwent()
        state, _ = table_gwent.apply(state, {"action": "pass"})
        self.assertEqual(state["turn"], "opponent")
        state, _ = table_gwent.apply(state, {"action": "pass"})
        self.assertEqual(state["round"], 2)
        self.assertEqual(state["sides"]["player"]["won"], 1)
        self.assertEqual(state["sides"]["opponent"]["won"], 1)
        self.assertEqual(state["turn"], "opponent")
        state, _ = table_gwent.apply(state, {"action": "pass"})
        state, _ = table_gwent.apply(state, {"action": "pass"})
        self.assertEqual(state["winner"], "draw")

    def test_scorch_destroys_strongest_non_hero(self):
        state = blank_gwent()
        strong = gwent_card("catapult")  # 8
        hero = gwent_card("geralt")  # 15, immune
        weak = gwent_card("poor_infantry")  # 1
        state["sides"]["player"]["rows"]["siege"] = [strong]
        state["sides"]["player"]["rows"]["melee"] = [hero, weak]
        state["sides"]["player"]["hand"] = [gwent_card("scorch")]
        state, _ = table_gwent.apply(state, {"action": "play", "card": 1})
        self.assertEqual(state["sides"]["player"]["rows"]["siege"], [])
        self.assertIn(hero, state["sides"]["player"]["rows"]["melee"])
        self.assertEqual(len(state["sides"]["player"]["rows"]["melee"]), 2)

    def test_engine_runs_the_opponent_reply(self):
        state = table_gwent.new_game(seed=11)
        card = state["sides"]["player"]["hand"][0]
        state, events = table_engine.apply(state, {"action": "play", "card": 1})
        self.assertTrue(any(e.startswith("Opponent") for e in events), events)
        if not state.get("winner") and state["round"] == 1:
            self.assertIn(state["turn"], ("player", "opponent"))

    def test_illegal_card_index_is_clean(self):
        state = blank_gwent()
        with self.assertRaises(GameError) as ctx:
            table_gwent.apply(state, {"action": "play", "card": 4})
        self.assertIn("hand is empty", str(ctx.exception))


class ArenaTests(unittest.TestCase):
    def blank(self) -> dict:
        state = table_arena.new_game(seed=1)
        for side in ("player", "opponent"):
            pile = state["sides"][side]
            pile["board"] = []
            pile["hand"] = []
            pile["deck"] = []
        state["turn"] = "player"
        state["sides"]["player"]["mana"] = 3
        state["sides"]["player"]["max_mana"] = 3
        return state

    def test_summon_pays_mana_and_has_sickness(self):
        state = self.blank()
        state["sides"]["player"]["hand"] = [arena_card("emberling")]  # 1 mana 1/2
        state["sides"]["player"]["mana"] = 1
        state, _ = table_arena.apply(state, {"action": "play", "card": 1})
        self.assertEqual(state["sides"]["player"]["mana"], 0)
        self.assertEqual(len(state["sides"]["player"]["board"]), 1)
        self.assertTrue(state["sides"]["player"]["board"][0]["sick"])

    def test_taunt_must_be_attacked_first(self):
        state = self.blank()
        state["sides"]["player"]["board"] = [
            {
                "name": "Raider",
                "attack": 2,
                "health": 2,
                "taunt": False,
                "sick": False,
                "attacked": False,
                "shield": False,
            }
        ]
        state["sides"]["opponent"]["board"] = [
            {
                "name": "Wall",
                "attack": 1,
                "health": 5,
                "taunt": True,
                "sick": False,
                "attacked": False,
                "shield": False,
            },
            {
                "name": "Grunt",
                "attack": 2,
                "health": 2,
                "taunt": False,
                "sick": False,
                "attacked": False,
                "shield": False,
            },
        ]
        with self.assertRaises(GameError) as ctx:
            table_arena.apply(
                state, {"action": "attack", "attacker": 1, "target": "2"}
            )
        self.assertIn("taunt", str(ctx.exception))
        table_arena.apply(state, {"action": "attack", "attacker": 1, "target": "1"})
        self.assertEqual(state["sides"]["opponent"]["board"][0]["health"], 3)

    def test_lethal_attack_wins(self):
        state = self.blank()
        state["sides"]["player"]["board"] = [
            {
                "name": "Finisher",
                "attack": 3,
                "health": 3,
                "taunt": False,
                "sick": False,
                "attacked": False,
                "shield": False,
            }
        ]
        state["sides"]["opponent"]["hero"] = 3
        state, _ = table_arena.apply(
            state, {"action": "attack", "attacker": 1, "target": "hero"}
        )
        self.assertEqual(state["winner"], "player")

    def test_end_turn_runs_the_ai_and_returns_turn(self):
        state = table_arena.new_game(seed=9)
        state, events = table_arena.apply(state, {"action": "end_turn"})
        self.assertGreater(len(events), 0)
        if not state.get("winner"):
            self.assertEqual(state["turn"], "player")
            self.assertEqual(state["sides"]["player"]["max_mana"], 2)


class HiddenInformationTests(unittest.TestCase):
    def test_public_view_never_carries_opponent_hand(self):
        state = table_engine.new_game("gwent", seed=5)
        view = table_render.public_view(state)
        self.assertNotIn("hand", view["sides"]["opponent"])
        self.assertGreater(view["sides"]["opponent"]["hand_count"], 0)
        self.assertIn("hand", view["sides"]["player"])

    def test_snapshot_is_counts_only(self):
        state = table_engine.new_game("arena", seed=5)
        snap = table_engine.board_snapshot(state)
        self.assertIsInstance(snap["opponent"]["hand"], int)
        self.assertIn("hero", snap["opponent"])
        self.assertNotIsInstance(snap["opponent"]["hand"], list)

    def test_tools_round_trip_and_hide_hand(self):
        from table_tools import h_new, h_play, h_state

        created = json.loads(h_new({"mode": "gwent", "seed": 5}))
        self.assertTrue(created["ok"])
        self.assertIn("board", created)
        played = json.loads(h_play({"action": "pass"}))
        self.assertTrue(played["ok"], played)
        shown = json.loads(h_state({}))
        self.assertTrue(shown["ok"])
        self.assertNotIn('"hand": [', json.dumps(shown["board"]))
        self.assertIn("hidden card", shown["board"])

    def test_tool_error_is_data(self):
        from table_tools import h_new, h_play

        h_new({"mode": "arena", "seed": 2})
        result = json.loads(h_play({"action": "play", "card": 99}))
        self.assertIn("error", result)
        self.assertIn("board", result)

    def test_store_round_trip(self):
        state = table_engine.new_game("arena", seed=3)
        table_store.save(state)
        loaded = table_store.load_active()
        self.assertEqual(loaded["game_id"], state["game_id"])
        snap_path = table_store.widget_path()
        self.assertTrue(snap_path.exists())
        payload = json.loads(snap_path.read_text())
        self.assertEqual(payload["mode"], "arena")


class PolishTests(unittest.TestCase):
    """The pre-publish fixes: AI pass discipline, widget install, art coverage."""

    def _fill(self, state: dict, side: str, count: int) -> None:
        state["sides"][side]["hand"] = [gwent_card("poor_infantry") for _ in range(count)]

    def test_ai_keeps_pressure_at_thirteen_point_lead(self):
        state = blank_gwent()
        state["sides"]["opponent"]["rows"]["ranged"] = [
            gwent_card("catapult"),  # 8
            gwent_card("ballista"),  # 6
        ]
        state["sides"]["player"]["rows"]["melee"] = [gwent_card("poor_infantry")]
        self._fill(state, "opponent", 9)
        self._fill(state, "player", 10)
        action = table_gwent.ai_action(state, "opponent")
        self.assertEqual(action["action"], "play", action)

    def test_ai_banks_a_twenty_two_point_lead(self):
        state = blank_gwent()
        state["sides"]["opponent"]["rows"]["ranged"] = [
            gwent_card("geralt"),  # 15
            gwent_card("catapult"),  # 8
        ]
        state["sides"]["player"]["rows"]["melee"] = [gwent_card("poor_infantry")]
        self._fill(state, "opponent", 9)
        self._fill(state, "player", 10)
        action = table_gwent.ai_action(state, "opponent")
        self.assertEqual(action["action"], "pass", action)

    def test_ai_banks_when_ahead_and_behind_on_cards(self):
        state = blank_gwent()
        state["sides"]["opponent"]["rows"]["siege"] = [
            gwent_card("mangonel"),
            gwent_card("mangonel"),
            gwent_card("mangonel"),
        ]
        state["sides"]["player"]["rows"]["melee"] = [gwent_card("poor_infantry")]
        self._fill(state, "opponent", 8)
        self._fill(state, "player", 10)
        action = table_gwent.ai_action(state, "opponent")
        self.assertEqual(action["action"], "pass", action)

    def test_widget_install_is_idempotent(self):
        result = table_store.install_widget()
        self.assertTrue(result.get("ok"), result)
        path = Path(result["path"])
        self.assertTrue(path.is_file())
        self.assertEqual(path, table_store.hermes_home() / "tui-widgets" / "table-board.mjs")
        again = table_store.install_widget()
        self.assertTrue(again.get("ok"))
        self.assertEqual(again["status"], "current")

    def test_every_card_has_art(self):
        keys = set()
        for faction in table_cards.GWENT_POOLS:
            keys.update(card["key"] for card in table_cards.build_gwent_deck(faction))
        for deck in table_cards.ARENA_POOLS:
            keys.update(card["key"] for card in table_cards.build_arena_deck(deck))
        missing = keys - set(table_cards.ART_BY_KEY)
        self.assertFalse(missing, missing)
        root = Path(__file__).resolve().parents[1]
        for stem in set(table_cards.ART_BY_KEY.values()):
            self.assertTrue((root / "art" / f"{stem}.webp").is_file(), stem)


class SelfPlayTests(unittest.TestCase):
    def _play(self, mode: str, seed: int, max_steps: int = 400) -> dict:
        state = table_engine.new_game(mode, seed)
        steps = 0
        while not state.get("winner") and steps < max_steps:
            if mode == "gwent":
                action = table_gwent.ai_action(state, state["turn"])
                state, _ = table_gwent.apply(state, action)
            else:
                table_arena.ai_take_turn(state, state["turn"])
            steps += 1
        self.assertIsNotNone(state.get("winner"), f"{mode} {seed} stalled")
        return state

    def test_both_modes_finish_for_eight_seeds(self):
        for seed in range(1, 9):
            self._play("gwent", seed)
            self._play("arena", seed)


if __name__ == "__main__":
    unittest.main()
