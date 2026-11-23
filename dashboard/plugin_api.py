"""Backend routes for the Table desktop page: /api/plugins/table/*.

The engine and store are the same modules the agent tools use, imported from
the plugin root. Every response is hand-free for the opponent.
"""

from __future__ import annotations

import base64
import re
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import table_cards  # noqa: E402
import table_engine  # noqa: E402
import table_store  # noqa: E402
from table_common import GameError  # noqa: E402
from table_render import public_view, render  # noqa: E402

router = APIRouter()
_LOCK = threading.Lock()
_ART_DIR = Path(__file__).resolve().parents[1] / "art"


@lru_cache(maxsize=128)
def _art_bytes(stem: str) -> bytes:
    path = _ART_DIR / f"{stem}.webp"
    return path.read_bytes() if path.is_file() else b""


class NewRequest(BaseModel):
    mode: str = "gwent"
    seed: int | None = None


class MoveRequest(BaseModel):
    action: str
    card: int | None = None
    row: str | None = None
    attacker: int | None = None
    target: str | int | None = None


def _broadcast(event: str, payload: dict[str, Any]) -> None:
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event

        broadcast_plugin_event("igni", event, payload)
    except Exception:
        pass


def _payload(state: dict, **extra: Any) -> dict:
    body = {
        "active": True,
        "view": public_view(state),
        "board": render(state),
        "winner": state.get("winner"),
    }
    body.update(extra)
    return body


@router.get("/state")
def get_state() -> dict:
    with _LOCK:
        state = table_store.load_active()
    if state is None:
        return {"active": False}
    return _payload(state)


@router.get("/rules")
def get_rules(mode: str | None = None) -> dict:
    with _LOCK:
        state = table_store.load_active()
    active_mode = mode or (state or {}).get("mode") or "gwent"
    try:
        name, text = table_engine.rules_text(active_mode)
    except GameError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "mode": name, "rules": text}


@router.post("/new")
def new_table(req: NewRequest) -> dict:
    try:
        state = table_engine.new_game(req.mode, seed=req.seed)
    except GameError as exc:
        return {"ok": False, "error": str(exc)}
    with _LOCK:
        table_store.save(state)
    _broadcast("started", {"mode": state["mode"], "game_id": state["game_id"]})
    return _payload(state, ok=True)


@router.post("/move")
def move(req: MoveRequest) -> dict:
    action: dict[str, Any] = {"action": req.action}
    for key in ("card", "row", "attacker", "target"):
        value = getattr(req, key)
        if value not in (None, ""):
            action[key] = value
    with _LOCK:
        state = table_store.load_active()
        if state is None:
            return {"ok": False, "error": "no active table — deal one first."}
        try:
            state, events = table_engine.apply(state, action)
        except GameError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "view": public_view(state),
                "board": render(state),
            }
        table_store.save(state)
    _broadcast(
        "moved",
        {
            "mode": state["mode"],
            "game_id": state["game_id"],
            "events": events,
            "winner": state.get("winner"),
        },
    )
    return _payload(state, ok=True, events=events)


@router.get("/health")
def health() -> dict:
    return {"ok": True, "plugin": "igni"}


@router.get("/art/{key}")
def get_art(key: str) -> dict:
    if not re.fullmatch(r"[a-z0-9_]{1,64}", key):
        return {"ok": False, "error": "invalid card key"}
    stem = table_cards.ART_BY_KEY.get(key)
    if stem is None and key in set(table_cards.ART_BY_KEY.values()) | {table_cards.ART_BACK}:
        stem = key
    if stem is None:
        return {"ok": False, "key": key, "error": "no art for that card"}
    data = _art_bytes(stem)
    if not data:
        return {"ok": False, "key": key, "stem": stem, "error": "art file missing"}
    return {
        "ok": True,
        "key": key,
        "stem": stem,
        "data_url": "data:image/webp;base64," + base64.b64encode(data).decode("ascii"),
    }
