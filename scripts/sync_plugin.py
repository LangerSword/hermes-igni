#!/usr/bin/env python3
"""Copy the checkout into the live Hermes home (and the TUI widget).

Usage:
    python3 scripts/sync_plugin.py            # install/refresh
    python3 scripts/sync_plugin.py --check    # exit 1 when the live copy drifts

The live plugin is a real copy, never a symlink: `hermes plugins validate`
rejects symlinks that escape the plugin root, and the desktop half is copied by
the app from the package folder.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        yield rel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    live = hermes_home() / "plugins" / "table"
    widget_src = repo / "tui" / "table-board.mjs"
    widget_dst = hermes_home() / "tui-widgets" / "table-board.mjs"

    drift = []
    for rel in iter_files(repo):
        target = live / rel
        if not target.exists() or not filecmp.cmp(repo / rel, target, shallow=False):
            drift.append(str(rel))
    if not widget_dst.exists() or not filecmp.cmp(widget_src, widget_dst, shallow=False):
        drift.append(str(widget_dst))

    if args.check:
        if drift:
            print("drift:")
            for item in drift:
                print(f"  {item}")
            return 1
        print("live copy is identical")
        return 0

    live.mkdir(parents=True, exist_ok=True)
    for rel in iter_files(repo):
        target = live / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / rel, target)
    widget_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(widget_src, widget_dst)

    # Drop stale files that no longer exist in the repo.
    keep = {str(rel) for rel in iter_files(repo)}
    for path in live.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(live))
            if rel not in keep and "__pycache__" not in rel:
                path.unlink()
    for path in sorted(live.rglob("__pycache__"), reverse=True):
        shutil.rmtree(path, ignore_errors=True)

    print(f"synced {live}")
    print(f"synced {widget_dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
