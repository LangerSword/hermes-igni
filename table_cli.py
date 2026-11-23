"""CLI and slash-command surfaces over the same engine the tools use."""

from __future__ import annotations

import argparse
import sys
from typing import Any

try:  # package import under Hermes
    from . import table_engine, table_store
    from .table_common import GameError
    from .table_render import render
except ImportError:  # standalone
    import table_engine  # type: ignore
    import table_store  # type: ignore
    from table_common import GameError  # type: ignore
    from table_render import render  # type: ignore


def _load() -> dict | None:
    return table_store.load_active()


def _board_text(state: dict | None, reveal: bool = False) -> str:
    if state is None:
        return "No table is set. Start one: /table new gwent  (or /table new arena)"
    return render(state, reveal=reveal)


def handle_slash(raw: str) -> str:
    parts = (raw or "").strip().split()
    cmd = parts[0].lower() if parts else "board"
    if cmd in ("board", "show", "state"):
        return _board_text(_load())
    if cmd == "rules":
        mode = parts[1] if len(parts) > 1 else ((_load() or {}).get("mode") or "gwent")
        try:
            _name, text = table_engine.rules_text(mode)
        except GameError as exc:
            return str(exc)
        return text
    if cmd == "new":
        mode = parts[1] if len(parts) > 1 else "gwent"
        seed = None
        if len(parts) > 2:
            try:
                seed = int(parts[2])
            except ValueError:
                return f"seed must be an integer, got {parts[2]!r}"
        try:
            state = table_engine.new_game(mode, seed=seed)
        except GameError as exc:
            return str(exc)
        table_store.save(state)
        return render(state)
    if cmd in ("help", "?"):
        return (
            "/table — show the active table\n"
            "/table rules [gwent|arena] — rules and card pool\n"
            "/table new [gwent|arena] [seed] — deal a new table\n"
            "Ask the agent to play: it relays your move through table_play."
        )
    return f"unknown /table command {cmd!r}; try /table help"


# ------------------------------------------------------------------ CLI ----


def setup_cli(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="table_command")

    board = sub.add_parser("board", help="show the active table")
    board.set_defaults(table_command="board")

    rules = sub.add_parser("rules", help="rules and card pool")
    rules.add_argument("mode", nargs="?", default=None, choices=["gwent", "arena"])

    new = sub.add_parser("new", help="deal a new table")
    new.add_argument("mode", nargs="?", default="gwent", choices=["gwent", "arena"])
    new.add_argument("--seed", type=int, default=None)

    demo = sub.add_parser("demo", help="AI vs AI, printed as a transcript")
    demo.add_argument("mode", nargs="?", default="gwent", choices=["gwent", "arena"])
    demo.add_argument("--seed", type=int, default=None)
    demo.add_argument("--max-steps", type=int, default=400)

    play = sub.add_parser("play", help="play a table in this terminal")
    play.add_argument("mode", nargs="?", default="gwent", choices=["gwent", "arena"])
    play.add_argument("--seed", type=int, default=None)

    parser.set_defaults(table_command=None)


def _describe_action(action: dict) -> str:
    move = action.get("action")
    if move == "play":
        text = f"play card {action.get('card')}"
        if action.get("row"):
            text += f" on {action['row']}"
        if action.get("target"):
            text += f" → {action['target']}"
        return text
    if move == "attack":
        return f"attack {action.get('target')} with minion {action.get('attacker')}"
    return str(move)


def _demo(mode: str, seed: int | None, max_steps: int) -> int:
    state = table_engine.new_game(mode, seed=seed)
    steps = 0
    while not state.get("winner") and steps < max_steps:
        if mode == "gwent":
            side = state["turn"]
            action = table_engine.MODES["gwent"].ai_action(state, side)
            state, events = table_engine.MODES["gwent"].apply(state, action)
            print(f"[r{state['round']}] {side}: {_describe_action(action)}")
            for event in events:
                print(f"    {event}")
        else:
            before = len(state["log"])
            side = state["turn"]
            table_engine.MODES["arena"].ai_take_turn(state, side)
            for event in state["log"][before:]:
                print(f"[t{state['turn_no']}] {side}: {event}")
        steps += 1
    print()
    print(render(state, reveal=True))
    if not state.get("winner"):
        print(f"\nstopped after {max_steps} steps without a winner")
        return 2
    return 0


def _interactive(mode: str, seed: int | None) -> int:
    state = table_engine.new_game(mode, seed=seed)
    table_store.save(state)
    print(render(state))
    print("\ntype 'h' for moves, 'q' to quit")
    while not state.get("winner"):
        try:
            raw = input("table> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        cmd = raw.lower()
        if cmd in ("q", "quit", "exit"):
            return 0
        if cmd in ("h", "help", "?"):
            print(table_engine.MODES[mode].legal_hint(state))
            if mode == "arena":
                print("attack syntax: a <your minion#> <enemy minion#|hero>")
            continue
        action: dict[str, Any]
        try:
            if mode == "gwent" and cmd in ("p", "pass"):
                action = {"action": "pass"}
            elif mode == "arena" and cmd in ("e", "end", "end_turn"):
                action = {"action": "end_turn"}
            elif mode == "arena" and cmd.startswith("a "):
                parts = raw.split()
                if len(parts) < 3:
                    print("attack syntax: a <your minion#> <enemy minion#|hero>")
                    continue
                action = {
                    "action": "attack",
                    "attacker": int(parts[1]),
                    "target": parts[2],
                }
            else:
                parts = raw.split()
                card_index = int(parts[0])
                card = state["sides"]["player"]["hand"][card_index - 1]
                action = {"action": "play", "card": card_index}
                if mode == "gwent" and card.get("kind") == "horn":
                    row = parts[1] if len(parts) > 1 else input("row (melee/ranged/siege): ").strip()
                    action["row"] = row
                if mode == "arena":
                    needs_target = (
                        card.get("kind") == "spell"
                        and (card.get("spell") or {}).get("type") == "damage"
                    )
                    if needs_target:
                        target = parts[1] if len(parts) > 1 else input(
                            "target (hero or enemy board#): "
                        ).strip()
                        action["target"] = target or "hero"
        except (ValueError, IndexError):
            print("not a move — type 'h' for help")
            continue
        try:
            state, events = table_engine.apply(state, action)
        except GameError as exc:
            print(f"illegal: {exc}")
            continue
        table_store.save(state)
        print()
        for event in events:
            print(f"  {event}")
        print()
        print(render(state))
    print(f"\n{table_engine.MODES[mode].legal_hint(state)}")
    return 0


def handle_cli(args: Any) -> int:
    command = getattr(args, "table_command", None) or "board"
    if command == "board":
        print(_board_text(_load()))
        return 0
    if command == "rules":
        mode = getattr(args, "mode", None) or ((_load() or {}).get("mode") or "gwent")
        try:
            _name, text = table_engine.rules_text(mode)
        except GameError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(text)
        return 0
    if command == "new":
        try:
            state = table_engine.new_game(args.mode, seed=args.seed)
        except GameError as exc:
            print(exc, file=sys.stderr)
            return 1
        table_store.save(state)
        print(render(state))
        return 0
    if command == "demo":
        return _demo(args.mode, args.seed, args.max_steps)
    if command == "play":
        return _interactive(args.mode, args.seed)
    print(f"unknown table command {command!r}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="table", description="Card games inside Hermes (Gwent / Arena)"
    )
    setup_cli(parser)
    return handle_cli(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
