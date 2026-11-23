# Verification

Run on 2026-11-24 on the author's Arch/Hyprland machine, Hermes Agent v0.23.1.

## Engine and tools

```text
$ python3 -m unittest discover -s tests -v
Ran 29 tests in 0.275s
OK
```

Covers: deck sizes (22/20), weather + horn + hero scoring, spy draw, scorch,
round ties and match draws, mana/summon/sickness, taunt enforcement, lethal,
AI end-turn, AI pass discipline (a 13-point lead keeps pressure; 17+ with card
disadvantage banks), hidden-hand boundaries in `public_view` / snapshot / tools,
tool errors as JSON, widget install, art coverage, store round-trip, FastAPI
routes (including `/art`), and AI-vs-AI termination.

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

## Live plugin

`hermes plugins enable table` loaded it into the gateway; after the v0.2 code
changes it was cycled with `disable` + `enable` so the running module matched
the installed files.

```text
$ hermes table install-widget
TUI widget current: /home/lakshaya/.hermes/tui-widgets/table-board.mjs
Run /table-board in the TUI to open it.
```

`table_new` also installs the widget on first use (tested idempotent), so a Git
install does not need the sync script for the scoreboard.

A one-shot Hermes session with the `table` toolset called `table_state` and
returned the board verbatim, with the opponent's `10 hidden card(s)` — no hand
leak. A previous `table_play` turn relayed `play card 1` and the opponent
answered inside the same call:

```text
You play Poor Infantry (1) to melee.
Opponent play Tibor Eggebracht (10) to ranged.
```

## Art

- **Cover:** `cover/cover.html` rendered by `scripts/render_cover.py` to
  `docs/cover.png` at 1600×900. Newsprint, halftone, cobalt / vermilion / acid
  inks, registration crosses, coupon and a fanned pixel hand. The type is real
  Anton / Playfair / IBM Plex Mono, not generated lettering.
- **Cards:** 21 WebP files in `art/`, each 256×256 and quantized to 24 colours
  from a 1K generation. The contact sheet is `docs/card-art-grid.png`.
  `scripts/build_card_art.py` rebuilds them from the raw cache.
- **API:** `GET /api/plugins/table/art/gwent_infantry` returns `ok=True` with a
  `data:image/webp;base64,...` payload (tested with FastAPI TestClient).
  Unknown keys return `ok=False`.
- **Desktop page:** rendered through the plugin's own SDK harness with a
  fixture (`test/harness.html` + `scripts/render_ui_harness.py`) at 1100×800.
  `docs/desktop.png` shows the 8-card hand, both Gwent sides, the pixel art,
  the scanline panels and the action bar. This also proves the art effect does
  not crash the page.
- **Packaged app:** the earlier pre-art version was played end-to-end in the
  real app (Sigismund Dijkstra → Play; score 14, hand/deck updated, separate
  `hermes table board` read the same state). The refreshed desktop half is
  copied and current; the app needs one relaunch/Rescan to load the new UI.
  The GUI launch was not repeated after the art change because launching the
  desktop is a user-approved action.

## TUI

```text
[tui-parent] 2026-11-23T17:28:03.360Z user widgets registered: table-board
```

The ambient scoreboard reads the hand-free snapshot at
`~/.hermes/table/board.json`; `table_new` now installs it automatically.
