#!/usr/bin/env python3
"""Load the plugin the way Hermes does, then drive the registered surface.

No Hermes process, no install: the repo __init__.py is imported as a package,
register() runs against a recording ctx, and one tool handler is executed to
prove the wiring answers as data. This is the served-surface proof the validator
does not give you (it never invokes a handler).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="hermes-table-load-"))
import os  # noqa: E402

os.environ["TABLE_DATA_DIR"] = str(TMP / "data")
os.environ["TABLE_HOME"] = str(TMP / "home")


class RecordingCtx:
    def __init__(self) -> None:
        self.tools = {}
        self.commands = {}
        self.cli = {}
        self.hooks = {}
        self.prompts = {}

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = (handler, kwargs)

    def register_cli_command(self, name, **kwargs):
        self.cli[name] = kwargs

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def register_system_prompt_section(self, *args, **kwargs):
        self.prompts[args[0]] = kwargs


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "table_plugin",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["table_plugin"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    plugin = load_plugin()
    ctx = RecordingCtx()
    plugin.register(ctx)

    expected = {"table_new", "table_play", "table_state", "table_rules"}
    assert set(ctx.tools) == expected, set(ctx.tools)
    assert "table" in ctx.commands
    assert "table" in ctx.cli
    assert "table" in ctx.prompts
    assert ctx.hooks == {}

    new = json.loads(ctx.tools["table_new"]["handler"]({"mode": "gwent", "seed": 7}))
    assert new.get("ok"), new
    played = json.loads(ctx.tools["table_play"]["handler"]({"action": "pass"}))
    assert played.get("ok"), played
    shown = json.loads(ctx.tools["table_state"]["handler"]({}))
    assert shown.get("ok"), shown
    rules = json.loads(ctx.tools["table_rules"]["handler"]({"mode": "arena"}))
    assert rules.get("ok") and "ARENA" in rules["rules"]
    print(
        "smoke_load ok:",
        len(ctx.tools),
        "tools,",
        list(ctx.commands),
        "command,",
        list(ctx.cli),
        "cli,",
        "prompt section",
        list(ctx.prompts),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
