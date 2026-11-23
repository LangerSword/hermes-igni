# Verification

Run on 2026-11-23 on the author's Arch/Hyprland machine, Hermes Agent v0.23.1.

## Engine and tools

```text
$ python3 -m unittest discover -s tests -v
Ran 23 tests in 0.404s
OK
```

Covers: deck sizes (22/20), weather + horn + hero scoring, spy draw, scorch,
round ties and match draws, mana/summon/sickness, taunt enforcement, lethal,
AI end-turn, hidden-hand boundaries in `public_view` / snapshot / tools, tool
errors as JSON, store round-trip, FastAPI routes, and AI-vs-AI termination.

```text
$ python3 smoke_test.py
self-play ok: {'player': 29, 'opponent': 11, 'draw': 0}
```

Forty self-played matches (20 seeds × 2 modes), every one terminating with a
winner. The player-side bias is expected: the player moves first in both modes.

```text
$ python3 smoke_load.py
smoke_load ok: 4 tools, ['table'] command, ['table'] cli, prompt section ['table']
```

This imports the repo `__init__.py` as a package, calls the real `register()`
against a recording ctx, asserts declared == registered, then drives
`table_new`, `table_play`, `table_state` and `table_rules` through the
registered handlers.

## Plugin validation

```text
$ hermes plugins validate /home/lakshaya/projects/hermes-table
✓ manifest — plugin.yaml parses
✓ loadable — entry: __init__.py, desktop/plugin.js
✓ capability probe — register() ran in isolation
✓ declared tools — matches registrations
✓ declared hooks — matches registrations
✓ built-in tool collisions — no collisions
✓ security scan — safe
✓ desktop surface — stays inside the plugin SDK surface
Validation passed.

$ hermes plugins doctor /home/lakshaya/.hermes/plugins/table
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 4 tool(s), 0 hook(s)
```

## Real agent turn

A one-shot Hermes session with the `table` toolset, after `hermes plugins
enable table`:

```text
$ hermes -m deepseek/deepseek-v4.1-flash-1017 --provider nous -t table \
    -z "Use table_state to show the current card table, then stop."
```

The model called `table_state` and returned the board verbatim, with the
opponent's `10 hidden card(s)` — no hand leak.

A second turn relayed one user move:

```text
$ hermes ... -z "The user's move is: play card 1. Relay exactly that move..."
Events:
  You play Poor Infantry (1) to melee.
  Opponent play Tibor Eggebracht (10) to ranged.
```

The opponent answered inside the same `table_play` call, and the board advanced.

## Desktop app

The app was launched from the packaged build, copied the unified package's
desktop half to

```text
~/.hermes/desktop-plugins/table/plugin.js
~/.hermes/desktop-plugins/table/.hermes-package.json
```

with the expected marker (`package: table`, source
`.../plugins/table/desktop`). After enabling the desktop half, the app loaded:

- sidebar row **Table**
- ⌘K entry **Table: open the card table**
- statusbar chip **♠ table**
- page at **#/table** backed by `/api/plugins/table`

A real move was made through the desktop page: clicked
**Sigismund Dijkstra** in hand, then **Play**. The backend returned:

```text
You send Sigismund Dijkstra (4) to the enemy row and draw 2.
Opponent pass.
```

and the page updated to opponent score 14 (Tibor 10 + Dijkstra 4), player hand
10 / deck 10. `hermes table board` from a separate process read the same state,
proving the writes are shared through the plugin store, not local UI state.
The screenshot is `docs/desktop.png`.

The desktop half was enabled through the app's own decision store
(`hermes.desktop.pluginDecisions.v2` → `{"table":true}`); it is
`defaultEnabled: false` in the package.

## TUI

```text
[tui-parent] 2026-11-23T17:28:03.360Z user widgets registered: table-board
```

The ambient scoreboard registered from `~/.hermes/tui-widgets/table-board.mjs`
and reads the hand-free snapshot at `~/.hermes/table/board.json`.
