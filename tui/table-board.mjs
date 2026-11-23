/**
 * Table — live TUI scoreboard.
 *
 * Reads the hand-free snapshot the plugin writes at
 * $HERMES_HOME/igni/board.json. Ambient only: it never takes the keyboard.
 * Open with /table-board; play through the agent tools (or the desktop page).
 */

import { readFileSync } from 'node:fs'

export default function register(sdk) {
  const { Dialog, Text, defineWidgetApp, h } = sdk
  const React = sdk.React
  const HOME = process.env.HERMES_HOME || `${process.env.HOME}/.hermes`
  const PATH = `${HOME}/igni/board.json`

  function read() {
    try {
      return JSON.parse(readFileSync(PATH, 'utf8'))
    } catch {
      return null
    }
  }

  function line(t, text, color) {
    return h(Text, { color: color || t.color.muted }, text)
  }

  function Live({ t }) {
    const [snap, setSnap] = React.useState(read)
    React.useEffect(() => {
      const timer = setInterval(() => setSnap(read()), 1000)
      return () => clearInterval(timer)
    }, [])

    if (!snap) {
      return h(
        Dialog,
        { width: 44 },
        line(t, 'TABLE', t.color.label),
        line(t, 'no table — ask for a game')
      )
    }
    const you = snap.player || {}
    const them = snap.opponent || {}
    const turn = snap.winner
      ? snap.winner === 'player'
        ? 'you win'
        : snap.winner === 'opponent'
          ? 'opponent wins'
          : 'draw'
      : snap.turn === 'player'
        ? 'your move'
        : 'opponent'
    const rows = []
    if (snap.mode === 'gwent') {
      rows.push(
        line(t, `GWENT · round ${snap.round}/3 · ${turn}`, t.color.label),
        line(t, `you ${you.score}  ──  ${them.score} opp`, t.color.primary),
        line(t, `hand ${you.hand} · deck ${you.deck} · won ${you.won}`),
        line(t, `opp hand ${them.hand} · deck ${them.deck} · won ${them.won}`)
      )
    } else {
      rows.push(
        line(t, `ARENA · turn ${snap.turn_no} · ${turn}`, t.color.label),
        line(t, `you ${you.hero}hp  ──  ${them.hero}hp opp`, t.color.primary),
        line(t, `mana ${you.mana}/${you.max_mana} · hand ${you.hand} · board ${you.board}`),
        line(t, `opp mana ${them.mana}/${them.max_mana} · hand ${them.hand} · board ${them.board}`)
      )
    }
    if (snap.last) {
      const last = String(snap.last)
      rows.push(line(t, last.length > 43 ? `${last.slice(0, 40)}…` : last))
    }
    return h(Dialog, { width: 44 }, ...rows)
  }

  defineWidgetApp({
    id: 'table-board',
    help: 'live scoreboard for the active card table',
    mode: 'ambient',
    zone: 'top-right',
    width: 46,
    init: () => ({}),
    reduce: state => state,
    render: ({ t }) => h(Live, { t })
  })
}
