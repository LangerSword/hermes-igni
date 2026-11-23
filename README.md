# Table

**Card games inside Hermes.** Two real, deterministic engines — a Gwent-shaped
row war and a Hearthstone-shaped mana duel — played against a rule-based
opponent that keeps its hand hidden. Play from chat with the agent, from a live
TUI scoreboard, or from a full desktop page with clickable cards.

No API keys. No network. Standard library only on the engine side.

![Table on the Hermes desktop](docs/desktop.png)


```text
GWENT · round 2/3 · your move

Opponent · Nilfgaard · score 26 · rounds 1 · hand 6 · deck 4
  melee  ▸ Impera Brigade 4 · Alba Pikemen 3          = 7
  ranged ▸ Black Infantry Archer 6                    = 6
  siege  ▸ Mangonel 6 · Menno Coehoorn 10             = 16
  hand    ▸ 6 hidden card(s)

You · Northern Realms · score 16 · rounds 0 · hand 7 · deck 4
  melee  ▸ Blue Stripes Commando 4 · Redanian Elite 5 = 9
  ranged ▸ —                                          = 0
  siege  ▸ Ballista 6                                 = 6

Weather: Biting Frost (melee)
Rounds won: you 0 — opponent 1

HAND
  [1] Ballista · siege · 6
  [2] Commander's Horn · special · double a row (add row)
  [3] Sigismund Dijkstra · spy · 4 · played to the enemy, draw 2
  ...

Your move: play <hand#> [row] for a horn, or pass.
```

## Why this exists

A game is a better demo of an agent than another dashboard. It has real state, a
visible opponent, hidden information, and a rule engine that says *no*. Table
puts that inside Hermes without turning the agent into a rules lawyer: the
engine validates every move, the agent relays yours, and the opponent's hand
never leaves the process.

## Modes

### Gwent — best of three, rows and weather

- Rows: melee, ranged, siege.
- Win two rounds. A round ends when both sides pass; a tie awards it to both.
- Weather sets every **non-hero** unit on one row to 1, for both sides.
- Commander's Horn doubles one of your rows. Clear Weather removes all weather.
- Spies join the enemy row and draw you two cards.
- Scorch destroys the strongest non-hero unit(s) on the board — both sides.
- Heroes are immune to weather. Hands and draw piles carry between rounds; the
  board, weather and horns clear.

### Arena — a mana duel to zero

- 30 health, mana 1→10, refill each turn, draw one.
- Minions have summoning sickness unless they have Charge.
- Taunts must be attacked first; Divine Shield absorbs the first hit.
- Battlecries: draw, heal, or damage all enemy minions.
- Empty deck deals rising fatigue damage.

Both decks and every card stat are original to this plugin. The rulesets are
inspired by the genres, not ports of a commercial game.

## Play from chat

The tools are `table_new`, `table_play`, `table_state`, `table_rules`.

```text
you    play gwent
hermes ┌──────────────────────────────┐
       │ table_new { mode: gwent }     │
       └──────────────────────────────┘
       [board, your move]

you    play 3
hermes ┌──────────────────────────────┐
       │ table_play { action: play,    │
       │              card: 3 }        │
       └──────────────────────────────┘
       You play Blue Stripes Commando (4) to melee.
       Opponent plays Impera Brigade (4) to melee.
       [new board]
```

Arena moves: `play <hand#>` (add a target for a damage spell),
`attack <your board#> <enemy board#|hero>`, `end turn`.
Gwent moves: `play <hand#>`, `play <hand#> <row>` for the horn, `pass`.

The agent is the referee, not the player: it asks for your move, relays it
exactly, and never reveals the hidden hand.

## Slash command

```text
/table                     show the active board
/table rules [mode]        rules + the full card pool
/table new [gwent|arena] [seed]
```

## Terminal

The CLI is a thin shim over the same engine, so it can also serve as the demo:

```bash
python3 table_cli.py demo gwent --seed 7     # AI vs AI, full transcript
python3 table_cli.py demo arena --seed 3
python3 table_cli.py play gwent              # play in this terminal
python3 table_cli.py rules arena
```

`hermes table …` is wired too when the plugin runs in-process; under
`plugins.isolation: host` the host skips CLI subcommands, so use the Python
entry point above.

## TUI

`tui/table-board.mjs` is an ambient scoreboard. `scripts/sync_plugin.py` copies
it to `$HERMES_HOME/tui-widgets/`; the TUI hot-loads it.

```text
/table-board
```

It reads the hand-free snapshot at `$HERMES_HOME/table/board.json` once a
second. It never includes the opponent's cards.

## Desktop

The same package ships the desktop half:

```text
desktop/plugin.js       full page at /table, clickable cards, sidebar nav row,
                        ⌘K "Table: open the card table", statusbar chip
dashboard/plugin_api.py /api/plugins/table/{state,new,move,rules}
```

The page plays both games without the chat agent: click a card, pick a row or
target, summon, attack, pass. It polls the backend and also subscribes to
`plugin.table.moved`.

The desktop half is opt-in: **Capabilities → Plugins → Table** (and **Rescan**
after installing). The Python half is gated separately by
`hermes plugins enable table`.

## Install

From this checkout:

```bash
python3 scripts/sync_plugin.py
hermes plugins enable table
```

Then start a new session (tools and the prompt section land next session; hooks
and slash commands hot-reload). Reload the TUI widgets with `/widgets-reload`
and open `/table-board`. In the desktop app, rescan plugins and enable Table.

Once the repo is published, `hermes plugins install LangerSword/hermes-table`
installs the same folder.

## Verify

```bash
python3 -m unittest discover -s tests -v   # 23 behaviour tests
python3 smoke_test.py --show               # both modes, 20 seeds, plus a board
python3 smoke_load.py                      # real register() + tool dispatch
hermes plugins validate .                  # manifest + capability probe
```

What the tests prove: deck sizes, weather/horn/hero scoring, spy draw, scorch,
round ties and match draws, mana/summon/taunt/lethal, AI turns finishing,
hidden-hand boundaries in `public_view`/snapshot/tools, tool errors as JSON,
persistence, backend routes, and AI-vs-AI termination on every seed.

## Layout

```text
__init__.py          register(): tools, /table, hermes table, prompt section
table_cards.py       original card pools, deck builders, rules text
table_common.py      GameError + side helpers
table_gwent.py       row war: scoring, weather, spies, horns, scorch, AI
table_arena.py       mana duel: combat, taunts, spells, battlecries, AI
table_render.py      chat board, structured public view, widget snapshot
table_engine.py      mode dispatch + the opponent's reply inside one call
table_store.py       profile-scoped state + atomic widget snapshot
table_tools.py       the four tool specs and handlers
table_cli.py         /table, hermes table, standalone CLI, interactive play
tui/table-board.mjs  ambient TUI scoreboard
desktop/plugin.js    desktop page
dashboard/           FastAPI router for the desktop page
tests/               stdlib unittest
scripts/sync_plugin.py
```

State lives in the plugin data directory (one active table per profile) and in
`$HERMES_HOME/table/board.json` for the widget. Both are JSON and atomic.

## Limits

- The AI is a heuristic opponent, not a tournament engine. It plays legal,
  tempo-aware moves; it will not surprise you with a meta deck.
- No multiplayer, no network, no persistence beyond the active table.
- The two modes are compact by design: a readable ruleset that fits in a tool
  result beats a card database.

## License

MIT. See [LICENSE](LICENSE).
