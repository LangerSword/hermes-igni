"""Persistence: one active table per profile, plus a hand-free widget snapshot.

State lives under the plugin data directory (profile-scoped). The TUI widget
reads a small JSON file at ``$HERMES_HOME/table/board.json``; that path is
documented and deliberately contains no hidden cards.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:  # package import under Hermes
    from .table_render import snapshot
except ImportError:  # standalone
    from table_render import snapshot  # type: ignore

PLUGIN_ID = "table"


def hermes_home() -> Path:
    env = os.environ.get("TABLE_HOME")
    if env:
        return Path(env).expanduser()
    try:
        from hermes_constants import get_hermes_home  # type: ignore

        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))


def data_dir() -> Path:
    env = os.environ.get("TABLE_DATA_DIR")
    if env:
        return Path(env).expanduser()
    try:
        from hermes_cli.plugins_state import PluginState  # type: ignore

        return Path(PluginState(PLUGIN_ID).data_dir)
    except Exception:
        digest = hashlib.sha256(PLUGIN_ID.encode("utf-8")).hexdigest()[:8]
        return hermes_home() / "plugin-data" / f"agent-plugin-{PLUGIN_ID}-{digest}"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def widget_path() -> Path:
    return hermes_home() / "table" / "board.json"


def save(state: dict) -> None:
    root = data_dir()
    games = root / "games"
    games.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        games / f"{state['game_id']}.json",
        json.dumps(state, ensure_ascii=False, indent=1),
    )
    _atomic_write(
        root / "active.json",
        json.dumps({"game_id": state["game_id"], "mode": state["mode"]}),
    )
    write_snapshot(state)


def write_snapshot(state: dict) -> None:
    payload = snapshot(state)
    payload["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write(widget_path(), json.dumps(payload, ensure_ascii=False))


def load_active() -> dict | None:
    root = data_dir()
    active = root / "active.json"
    if not active.exists():
        return None
    try:
        game_id = json.loads(active.read_text(encoding="utf-8")).get("game_id")
    except (OSError, ValueError):
        return None
    if not game_id:
        return None
    path = root / "games" / f"{game_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clear_active() -> None:
    active = data_dir() / "active.json"
    try:
        active.unlink()
    except OSError:
        pass
