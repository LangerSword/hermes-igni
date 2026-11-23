/**
 * Table — the desktop half.
 *
 * A full page at /table that plays both games against the Python engine through
 * /api/plugins/table. The pane is app-level (the unified package copies this
 * folder to desktop-plugins/table); the backend half must be enabled in
 * config.yaml (hermes plugins enable table).
 *
 * Plain ESM, loaded uncompiled: jsx() calls, no JSX syntax. Only
 * @hermes/plugin-sdk, react and react/jsx-runtime resolve.
 */

import {
  Button,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  host,
  queryClient,
  useQuery
} from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'
import { useEffect, useMemo, useState } from 'react'

const ID = 'igni'
const ROWS = ['melee', 'ranged', 'siege']

// Pixel-art cards are fetched once per key from /api/plugins/table/art/<key>
// and cached for the life of the window. The map is mutated, so artVersion
// forces a repaint when new keys land.
const artCache = new Map()

const C = {
  text: 'var(--ui-text-primary)',
  text2: 'var(--ui-text-secondary)',
  text3: 'var(--ui-text-tertiary)',
  text4: 'var(--ui-text-quaternary)',
  stroke: 'var(--ui-stroke-secondary)',
  panel: 'var(--ui-bg-quaternary)',
  hover: 'var(--chrome-action-hover)',
  accent: 'var(--ui-accent)'
}

const S = {
  page: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'auto',
    padding: '20px 24px 24px',
    gap: '14px',
    boxSizing: 'border-box',
    color: C.text
  },
  header: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    letterSpacing: '0.22em',
    textTransform: 'uppercase',
    color: C.text,
    fontFamily: 'var(--font-mono, monospace)'
  },
  subtitle: { fontSize: '11.5px', color: C.text3 },
  subtle: { fontSize: '11.5px', color: C.text3 },
  status: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '12px', color: C.text2 },
  board: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '12px',
    alignItems: 'stretch'
  },
  panel: {
    border: `2px solid ${C.stroke}`,
    borderRadius: '0',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '9px',
    minWidth: 0,
    backgroundImage:
      'repeating-linear-gradient(0deg, rgba(127,127,127,0.07) 0px, rgba(127,127,127,0.07) 1px, transparent 1px, transparent 4px)'
  },
  rowLabel: {
    fontSize: '10.5px',
    lineHeight: '14px',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: C.text4,
    whiteSpace: 'nowrap'
  },
  heroLine: { display: 'flex', alignItems: 'baseline', gap: '8px' },
  big: {
    fontFamily: 'var(--font-mono, monospace)',
    fontSize: '25px',
    lineHeight: '28px',
    fontWeight: 600,
    fontVariantNumeric: 'tabular-nums',
    color: C.text
  },
  rowWrap: { display: 'flex', alignItems: 'flex-start', gap: '8px' },
  rowCards: { display: 'flex', gap: '5px', flexWrap: 'wrap', flex: '1 1 auto', minWidth: 0 },
  rowScore: {
    fontFamily: 'var(--font-mono, monospace)',
    fontSize: '13px',
    fontVariantNumeric: 'tabular-nums',
    color: C.text2,
    paddingTop: '6px',
    minWidth: '22px',
    textAlign: 'right'
  },
  emptyRow: { fontSize: '12px', color: C.text4, paddingTop: '6px' },
  horn: {
    fontSize: '9.5px',
    letterSpacing: '0.06em',
    color: C.accent,
    border: `1px solid ${C.accent}`,
    borderRadius: '2px',
    padding: '2px 4px',
    marginTop: '4px',
    whiteSpace: 'nowrap'
  },
  handPanel: {
    border: `1px solid ${C.stroke}`,
    borderRadius: '5px',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '9px'
  },
  hand: { display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '3px' },
  actions: { display: 'flex', alignItems: 'center', gap: '7px', flexWrap: 'wrap' },
  selText: { fontSize: '11.5px', color: C.text2, marginRight: '2px' },
  error: {
    border: `1px solid ${C.stroke}`,
    borderLeft: `3px solid ${C.accent}`,
    borderRadius: '3px',
    padding: '8px 10px',
    fontSize: '12px',
    color: C.text,
    background: C.panel
  },
  winner: {
    border: `1px solid ${C.accent}`,
    borderRadius: '5px',
    padding: '10px 12px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap'
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '52px 20px',
    border: `1px dashed ${C.stroke}`,
    borderRadius: '6px'
  },
  modes: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', width: '100%', maxWidth: '680px' },
  modeCard: {
    border: `1px solid ${C.stroke}`,
    borderRadius: '5px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    textAlign: 'left',
    background: 'transparent',
    cursor: 'pointer',
    color: C.text
  },
  log: { display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' },
  logLine: { fontSize: '11px', lineHeight: '15px', color: C.text4 }
}

function Tile({ title, meta, note, selected, onClick, dim, accent, art, artHeight = 54 }) {
  const Comp = onClick ? 'button' : 'div'
  return jsxs(Comp, {
    type: onClick ? 'button' : undefined,
    onClick,
    disabled: undefined,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1px',
      alignItems: 'flex-start',
      textAlign: 'left',
      padding: '0',
      minWidth: '96px',
      maxWidth: '158px',
      borderRadius: '0',
      border: `2px solid ${selected ? C.accent : C.stroke}`,
      background: selected ? C.hover : C.panel,
      color: C.text,
      cursor: onClick ? 'pointer' : 'default',
      opacity: dim ? 0.45 : 1,
      font: 'inherit',
      overflow: 'hidden'
    },
    children: [
      art
        ? jsx('img', {
            src: art,
            alt: '',
            draggable: false,
            style: {
              display: 'block',
              width: '100%',
              height: `${artHeight}px`,
              objectFit: 'cover',
              imageRendering: 'pixelated',
              borderBottom: `1px solid ${C.stroke}`,
              background: C.panel
            }
          })
        : null,
      jsx('span', {
        style: {
          fontSize: '11.5px',
          lineHeight: '15px',
          fontWeight: 600,
          color: accent ? C.accent : C.text,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: '100%',
          padding: '4px 7px 0'
        },
        children: title
      }),
      meta
        ? jsx('span', {
            style: {
              fontSize: '10.5px',
              lineHeight: '14px',
              fontFamily: 'var(--font-mono, monospace)',
              color: C.text3,
              padding: '0 7px'
            },
            children: meta
          })
        : null,
      note
        ? jsx('span', {
            style: {
              fontSize: '9.5px',
              lineHeight: '13px',
              color: C.text4,
              padding: '0 7px 5px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: '100%'
            },
            children: note
          })
        : null
    ]
  })
}

function GwentSide({ side, view, artFor }) {
  const weatherRows = new Set((view.weather || []).map(w => w.row))
  return jsxs('div', {
    style: S.panel,
    children: [
      jsxs('div', {
        style: { display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline' },
        children: [
          jsx('span', { style: S.rowLabel, children: side.label }),
          jsx('span', { style: S.subtle, children: side.faction })
        ]
      }),
      jsxs('div', {
        style: S.heroLine,
        children: [
          jsx('span', { style: S.big, children: String(side.score) }),
          jsx('span', { style: S.subtle, children: `rounds ${side.won} · hand ${side.hand_count} · deck ${side.deck_count}` })
        ]
      }),
      ...ROWS.map(row => {
        const cards = side.rows?.[row] || []
        const horn = side.horns?.[row]
        const total =
          cards.reduce(
            (n, c) => n + (weatherRows.has(row) && c.kind !== 'hero' ? 1 : c.strength),
            0
          ) * (horn ? 2 : 1)
        return jsxs(
          'div',
          {
            style: S.rowWrap,
            children: [
              jsx('div', { style: { ...S.rowLabel, width: '46px', paddingTop: '7px' }, children: row }),
              jsxs('div', {
                style: S.rowCards,
                children: cards.length
                  ? cards.map((card, index) =>
                      jsx(
                        Tile,
                        {
                          title: card.name,
                          meta: String(card.strength),
                          accent: card.kind === 'hero',
                          art: artFor(card.key),
                          artHeight: 42
                        },
                        `${row}-${index}`
                      )
                    )
                  : jsx('span', { style: S.emptyRow, children: '—' })
              }),
              jsx('div', { style: S.rowScore, children: String(total) })
            ]
          },
          row
        )
      }),
      side.passed
        ? jsx('span', { style: { ...S.subtle, color: C.accent }, children: 'passed' })
        : null
    ]
  })
}

function ArenaSide({ side, view, opponent, selection, target, onOwnMinion, onEnemyMinion, onEnemyHero, artFor }) {
  const spellSelected =
    selection != null && selection.kind === 'spell' && selection.damage
  const canTarget = opponent && (selection?.kind === 'attacker' || spellSelected)
  return jsxs('div', {
    style: S.panel,
    children: [
      jsxs('div', {
        style: { display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline' },
        children: [
          jsx('span', { style: S.rowLabel, children: side.label }),
          jsx('span', {
            style: S.subtle,
            children: `mana ${side.mana}/${side.max_mana} · hand ${side.hand_count} · deck ${side.deck_count}`
          })
        ]
      }),
      jsxs('div', {
        style: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' },
        children: [
          jsx(Tile, {
            title: `${side.hero}/30`,
            meta: 'hero',
            selected: opponent && target === 'hero',
            onClick: canTarget ? onEnemyHero : undefined,
            accent: side.hero <= 10
          }),
          ...(side.board || []).map(minion =>
            jsx(
              Tile,
              {
                title: minion.name,
                meta: `${minion.attack}/${minion.health}`,
                note: [
                  minion.taunt ? 'taunt' : '',
                  minion.shield ? 'shield' : '',
                  minion.charge ? 'charge' : '',
                  minion.sick ? 'sick' : '',
                  minion.attacked ? 'done' : ''
                ]
                  .filter(Boolean)
                  .join(' · '),
                art: artFor(minion.key),
                artHeight: 40,
                selected:
                  (!opponent && selection?.kind === 'attacker' && selection.index === minion.index) ||
                  (opponent && target === String(minion.index)),
                onClick: opponent
                  ? canTarget
                    ? () => onEnemyMinion(minion)
                    : undefined
                  : () => onOwnMinion(minion)
              },
              `${opponent ? 'o' : 'p'}-${minion.index}`
            )
          )
        ]
      }),
      jsx('span', { style: S.subtle, children: side.fatigue ? `fatigue ${side.fatigue}` : '' })
    ]
  })
}

function handMeta(card, mode) {
  if (mode === 'gwent') {
    if (card.kind === 'unit' || card.kind === 'hero') return `${card.row} · ${card.strength}`
    if (card.kind === 'spy') return `spy · ${card.strength}`
    return 'special'
  }
  if (card.kind === 'minion') return `${card.cost} mana · ${card.attack}/${card.health}`
  const spell = card.spell || {}
  return `${card.cost} mana · ${spell.type || 'spell'}${spell.amount != null ? ` ${spell.amount}` : ''}`
}

function handNote(card, mode) {
  if (mode === 'gwent') {
    if (card.kind === 'horn') return 'double a row'
    if (card.kind === 'weather' || card.kind === 'clear' || card.kind === 'scorch') return card.text || ''
    if (card.kind === 'hero') return 'immune to weather'
    return ''
  }
  const flags = []
  if (card.taunt) flags.push('taunt')
  if (card.charge) flags.push('charge')
  if (card.shield) flags.push('shield')
  if (card.battlecry) flags.push(`battlecry ${card.battlecry.type}`)
  return flags.join(' · ')
}

function TablePage({ ctx }) {
  const q = useQuery({
    queryKey: ['table', 'state'],
    queryFn: () => ctx.rest('/state'),
    refetchInterval: 2000,
    refetchOnWindowFocus: true
  })
  const [handSel, setHandSel] = useState(null)
  const [attacker, setAttacker] = useState(null)
  const [row, setRow] = useState('')
  const [target, setTarget] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [, setArtVersion] = useState(0)

  const data = q.data
  const view = data && data.active ? data.view : null
  const mode = view ? view.mode : 'gwent'
  const hand = view ? view.sides.player.hand || [] : []
  const canAct = Boolean(view && view.turn === 'player' && !view.winner && !busy)
  const selectedCard = hand.find(c => c.index === handSel) || null
  const selection = selectedCard
    ? {
        kind: selectedCard.kind,
        index: selectedCard.index,
        damage: selectedCard.kind === 'spell' && selectedCard.spell?.type === 'damage'
      }
    : attacker != null
      ? { kind: 'attacker', index: attacker }
      : null

  const artKeys = useMemo(() => {
    const keys = new Set(['card_back'])
    if (!view) return [...keys]
    for (const card of view.sides.player.hand || []) if (card.key) keys.add(card.key)
    if (view.mode === 'gwent') {
      for (const side of [view.sides.player, view.sides.opponent]) {
        for (const row of ROWS) {
          for (const card of side.rows?.[row] || []) if (card.key) keys.add(card.key)
        }
      }
    } else {
      for (const side of [view.sides.player, view.sides.opponent]) {
        for (const minion of side.board || []) if (minion.key) keys.add(minion.key)
      }
    }
    return [...keys].sort()
  }, [view])
  const artSignature = artKeys.join('|')

  useEffect(() => {
    let alive = true
    const missing = artKeys.filter(key => !artCache.has(key))
    if (!missing.length) return undefined
    ;(async () => {
      let changed = false
      for (const key of missing) {
        try {
          const res = await ctx.rest('/art/' + encodeURIComponent(key))
          if (res && res.data_url) {
            artCache.set(key, res.data_url)
            changed = true
          }
        } catch {
          // The backend may be disabled; the text card still works.
        }
      }
      if (alive && changed) setArtVersion(value => value + 1)
    })()
    return () => {
      alive = false
    }
  }, [artSignature])

  const artFor = key => (key ? artCache.get(key) : undefined)

  const clearSelection = () => {
    setHandSel(null)
    setAttacker(null)
    setRow('')
    setTarget(null)
  }

  async function post(path, body) {
    setBusy(true)
    setError('')
    try {
      const res = await ctx.rest(path, { method: 'POST', body })
      if (res && res.error) {
        setError(res.error)
        return false
      }
      clearSelection()
      await q.refetch()
      return true
    } catch (err) {
      setError(String((err && err.message) || err))
      return false
    } finally {
      setBusy(false)
    }
  }

  function newGame(nextMode) {
    void post('/new', { mode: nextMode || mode })
  }

  function onHand(card) {
    if (!canAct) return
    if (handSel === card.index) {
      clearSelection()
      return
    }
    setHandSel(card.index)
    setAttacker(null)
    setRow('')
    setTarget(null)
  }

  function onOwnMinion(minion) {
    if (!canAct || mode !== 'arena') return
    setAttacker(attacker === minion.index ? null : minion.index)
    setHandSel(null)
    setTarget(null)
  }

  function onEnemyMinion(minion) {
    if (!canAct) return
    if (selectedCard && selectedCard.kind === 'spell' && selectedCard.spell?.type === 'damage') {
      setTarget(String(minion.index))
      return
    }
    if (attacker != null) {
      void post('/move', { action: 'attack', attacker, target: String(minion.index) })
    }
  }

  function onEnemyHero() {
    if (!canAct) return
    if (selectedCard && selectedCard.kind === 'spell' && selectedCard.spell?.type === 'damage') {
      setTarget('hero')
      return
    }
    if (attacker != null) {
      void post('/move', { action: 'attack', attacker, target: 'hero' })
    }
  }

  function playSelected() {
    if (!selectedCard || !canAct) return
    const action = { action: 'play', card: selectedCard.index }
    if (mode === 'gwent' && selectedCard.kind === 'horn') {
      if (!row) {
        setError('pick a row for the horn first.')
        return
      }
      action.row = row
    }
    if (mode === 'arena' && selectedCard.kind === 'spell' && selectedCard.spell?.type === 'damage') {
      if (!target) {
        setError('pick a target first.')
        return
      }
      action.target = target
    }
    void post('/move', action)
  }

  function turnAction() {
    if (!canAct) return
    void post('/move', { action: mode === 'gwent' ? 'pass' : 'end_turn' })
  }

  function concede() {
    if (!view || view.winner) return
    void post('/move', { action: 'concede' })
  }

  const header = jsxs('div', {
    style: S.header,
    children: [
      jsx('div', { style: S.title, children: 'IGNI' }),
      jsx('span', {
        style: {
          color: C.accent,
          fontFamily: 'var(--font-mono, monospace)',
          fontSize: '18px',
          lineHeight: '18px'
        },
        children: '▮'
      }),
      jsx('div', { style: { ...S.subtle, flex: '1 1 auto' }, children: 'The fire sign · Gwent / Arena' }),
      jsx(Button, {
        size: 'xs',
        variant: 'outline',
        onClick: () => newGame('gwent'),
        disabled: busy,
        children: 'New Gwent'
      }),
      jsx(Button, {
        size: 'xs',
        variant: 'outline',
        onClick: () => newGame('arena'),
        disabled: busy,
        children: 'New Arena'
      })
    ]
  })

  if (q.error) {
    return jsxs('div', {
      style: S.page,
      children: [
        header,
        jsx('div', {
          style: S.error,
          children:
            'The Table backend is not reachable. Enable the plugin (hermes plugins enable table) and restart the gateway, then rescan desktop plugins.'
        })
      ]
    })
  }

  if (q.isLoading) {
    return jsxs('div', { style: S.page, children: [header, jsx('div', { style: S.subtle, children: 'shuffling…' })] })
  }

  if (!view) {
    return jsxs('div', {
      style: S.page,
      children: [
        header,
        jsxs('div', {
          style: S.empty,
          children: [
            artFor('card_back')
              ? jsx('img', {
                  src: artFor('card_back'),
                  alt: '',
                  draggable: false,
                  style: {
                    width: '128px',
                    height: '128px',
                    imageRendering: 'pixelated',
                    border: `2px solid ${C.stroke}`
                  }
                })
              : null,
            jsx('div', { style: S.title, children: 'Deal a table' }),
            jsx('div', { style: S.subtle, children: 'Both games run on the same engine the agent tools use.' }),
            jsxs('div', {
              style: S.modes,
              children: [
                jsxs('button', {
                  type: 'button',
                  style: S.modeCard,
                  onClick: () => newGame('gwent'),
                  children: [
                    jsx('span', { style: { fontSize: '14px', fontWeight: 600 }, children: 'Gwent' }),
                    jsx('span', {
                      style: S.subtle,
                      children: 'Rows, weather, spies, horns and scorch. Best of three.'
                    })
                  ]
                }),
                jsxs('button', {
                  type: 'button',
                  style: S.modeCard,
                  onClick: () => newGame('arena'),
                  children: [
                    jsx('span', { style: { fontSize: '14px', fontWeight: 600 }, children: 'Arena' }),
                    jsx('span', {
                      style: S.subtle,
                      children: '30 health, mana, taunts, charge and divine shields.'
                    })
                  ]
                })
              ]
            })
          ]
        })
      ]
    })
  }

  const status =
    mode === 'gwent'
      ? `GWENT · round ${view.round}/3 · ${view.turn === 'player' ? 'your move' : 'opponent'}${
          view.winner ? ` · ${view.winner === 'player' ? 'you win' : view.winner === 'opponent' ? 'opponent wins' : 'draw'}` : ''
        }`
      : `ARENA · turn ${view.turn_no} · ${view.turn === 'player' ? 'your move' : 'opponent'}${
          view.winner ? ` · ${view.winner === 'player' ? 'you win' : view.winner === 'opponent' ? 'opponent wins' : 'draw'}` : ''
        }`

  const winnerText =
    view.winner === 'player' ? 'You win.' : view.winner === 'opponent' ? 'Opponent wins.' : 'Draw.'

  return jsxs('div', {
    style: S.page,
    children: [
      header,
      jsxs('div', {
        style: S.status,
        children: [
          jsx('span', { style: S.rowLabel, children: status }),
          view.winner
            ? null
            : jsx('span', { style: S.subtle, children: busy ? 'opponent moving…' : 'the engine keeps the opponent hand hidden' })
        ]
      }),
      error ? jsx('div', { style: S.error, children: error }) : null,
      view.winner
        ? jsxs('div', {
            style: S.winner,
            children: [
              jsx('span', { style: { fontSize: '14px', fontWeight: 600 }, children: winnerText }),
              jsx(Button, { size: 'xs', variant: 'secondary', onClick: () => newGame(mode), children: 'Rematch' }),
              jsx(Button, { size: 'xs', variant: 'outline', onClick: () => newGame(mode === 'gwent' ? 'arena' : 'gwent'), children: 'Other game' })
            ]
          })
        : null,
      jsxs('div', {
        style: S.board,
        children: [
          mode === 'gwent'
            ? jsx(GwentSide, { side: view.sides.opponent, view, artFor })
            : jsx(ArenaSide, {
                side: view.sides.opponent,
                view,
                opponent: true,
                selection,
                target,
                onEnemyMinion,
                onEnemyHero,
                artFor
              }),
          mode === 'gwent'
            ? jsx(GwentSide, { side: view.sides.player, view, artFor })
            : jsx(ArenaSide, {
                side: view.sides.player,
                view,
                opponent: false,
                selection,
                target,
                onOwnMinion,
                artFor
              })
        ]
      }),
      jsxs('div', {
        style: S.handPanel,
        children: [
          jsxs('div', {
            style: { display: 'flex', justifyContent: 'space-between', gap: '10px' },
            children: [
              jsx('span', { style: S.rowLabel, children: 'Your hand' }),
              jsx('span', {
                style: S.subtle,
                children: `${hand.length} card${hand.length === 1 ? '' : 's'} · deck ${view.sides.player.deck_count}`
              })
            ]
          }),
          jsxs('div', {
            style: S.hand,
            children: hand.length
              ? hand.map(card =>
                  jsx(
                    Tile,
                    {
                      title: card.name,
                      meta: handMeta(card, mode),
                      note: handNote(card, mode),
                      art: artFor(card.key),
                      artHeight: 62,
                      selected: handSel === card.index,
                      onClick: canAct ? () => onHand(card) : undefined,
                      dim: !canAct,
                      accent: card.kind === 'hero'
                    },
                    `h-${card.index}`
                  )
                )
              : jsx('span', { style: S.subtle, children: 'empty hand' })
          }),
          jsxs('div', {
            style: S.actions,
            children: [
              selectedCard ? jsx('span', { style: S.selText, children: selectedCard.name }) : null,
              selectedCard && mode === 'gwent' && selectedCard.kind === 'horn'
                ? ROWS.map(r =>
                    jsx(
                      Button,
                      {
                        size: 'xs',
                        variant: row === r ? 'secondary' : 'outline',
                        onClick: () => setRow(r),
                        children: r
                      },
                      `row-${r}`
                    )
                  )
                : null,
              selectedCard && mode === 'arena' && selectedCard.kind === 'spell' && selectedCard.spell?.type === 'damage'
                ? [
                    jsx(
                      Button,
                      {
                        size: 'xs',
                        variant: target === 'hero' ? 'secondary' : 'outline',
                        onClick: () => setTarget('hero'),
                        children: 'hero'
                      },
                      'target-hero'
                    ),
                    ...(view.sides.opponent.board || []).map(m =>
                      jsx(
                        Button,
                        {
                          size: 'xs',
                          variant: target === String(m.index) ? 'secondary' : 'outline',
                          onClick: () => setTarget(String(m.index)),
                          children: `[${m.index}] ${m.name}`
                        },
                        `target-${m.index}`
                      )
                    )
                  ]
                : null,
              selectedCard
                ? jsx(Button, {
                    size: 'sm',
                    variant: 'default',
                    disabled: !canAct,
                    onClick: playSelected,
                    children:
                      selectedCard.kind === 'minion'
                        ? 'Summon'
                        : selectedCard.kind === 'spell'
                          ? 'Cast'
                          : 'Play'
                  })
                : null,
              selectedCard || attacker != null
                ? jsx(Button, { size: 'xs', variant: 'ghost', onClick: clearSelection, children: 'Cancel' })
                : null,
              attacker != null
                ? jsx('span', {
                    style: S.selText,
                    children: `minion ${attacker} ready — pick an enemy target`
                  })
                : null,
              jsx(Button, {
                size: 'sm',
                variant: 'secondary',
                disabled: !canAct,
                onClick: turnAction,
                children: mode === 'gwent' ? 'Pass' : 'End turn'
              }),
              jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                disabled: Boolean(view.winner) || busy,
                onClick: concede,
                children: 'Concede'
              })
            ]
          }),
          jsxs('div', {
            style: S.log,
            children: (view.log || []).slice(-3).map((line, index) =>
              jsx('div', { style: S.logLine, children: line }, `log-${index}`)
            )
          })
        ]
      })
    ]
  })
}

function TableChip() {
  return jsx('button', {
    type: 'button',
    title: 'Open the card table',
    onClick: () => host.navigate('/igni'),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      height: '100%',
      padding: '0 6px',
      border: 'none',
      background: 'transparent',
      color: 'var(--ui-text-tertiary)',
      cursor: 'pointer',
      fontSize: '11px'
    },
    children: '🔥 igni'
  })
}

export default {
  id: ID,
  name: 'Igni',
  defaultEnabled: true,
  register(ctx) {
    ctx.register({
      id: 'page',
      area: ROUTES_AREA,
      data: { path: '/igni' },
      render: () => jsx(TablePage, { ctx })
    })

    ctx.register({
      id: 'nav',
      area: SIDEBAR_NAV_AREA,
      data: { path: '/igni', label: 'Igni', codicon: 'symbol-event' }
    })

    ctx.register({
      id: 'open',
      area: PALETTE_AREA,
      data: {
        id: 'igni.open',
        label: 'Igni: open the card table',
        keywords: ['table', 'cards', 'gwent', 'arena', 'hearthstone', 'game'],
        run: () => host.navigate('/igni')
      }
    })

    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 140,
      render: () => jsx(TableChip, {})
    })

    host.onEvent('plugin.igni.moved', () => {
      queryClient.invalidateQueries({ queryKey: ['table', 'state'] })
    })
  }
}
