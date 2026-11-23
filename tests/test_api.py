"""Backend route tests: mounted at /api/plugins/table, same engine as the tools."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="hermes-table-api-"))
os.environ["TABLE_DATA_DIR"] = str(_TMP / "data")
os.environ["TABLE_HOME"] = str(_TMP / "home")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import plugin_api  # noqa: E402

app = FastAPI()
app.include_router(plugin_api.router, prefix="/api/plugins/table")
client = TestClient(app)


class ApiTests(unittest.TestCase):
    def test_empty_state(self):
        plugin_api.table_store.clear_active()
        payload = client.get("/api/plugins/table/state").json()
        self.assertFalse(payload["active"])

    def test_new_move_state(self):
        created = client.post(
            "/api/plugins/table/new", json={"mode": "gwent", "seed": 5}
        ).json()
        self.assertTrue(created["ok"])
        view = created["view"]
        self.assertEqual(view["mode"], "gwent")
        self.assertNotIn("hand", view["sides"]["opponent"])
        self.assertIn("hand", view["sides"]["player"])

        moved = client.post(
            "/api/plugins/table/move", json={"action": "pass"}
        ).json()
        self.assertTrue(moved["ok"], moved)
        self.assertTrue(moved["events"])
        self.assertIn("view", moved)

        state = client.get("/api/plugins/table/state").json()
        self.assertTrue(state["active"])
        self.assertEqual(state["view"]["game_id"], created["view"]["game_id"])

    def test_bad_move_keeps_the_table(self):
        client.post("/api/plugins/table/new", json={"mode": "arena", "seed": 2})
        bad = client.post(
            "/api/plugins/table/move", json={"action": "play", "card": 99}
        ).json()
        self.assertFalse(bad["ok"])
        self.assertIn("error", bad)
        good = client.get("/api/plugins/table/state").json()
        self.assertTrue(good["active"])

    def test_rules(self):
        payload = client.get("/api/plugins/table/rules", params={"mode": "arena"}).json()
        self.assertTrue(payload["ok"])
        self.assertIn("ARENA", payload["rules"])

    def test_art(self):
        payload = client.get("/api/plugins/table/art/gwent_infantry").json()
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["data_url"].startswith("data:image/webp;base64,"))
        self.assertGreater(len(payload["data_url"]), 1000)
        missing = client.get("/api/plugins/table/art/not_a_card").json()
        self.assertFalse(missing["ok"])


if __name__ == "__main__":
    unittest.main()
