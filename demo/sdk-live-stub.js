import React, { useEffect, useMemo, useRef, useState } from 'react'

export { React, useEffect, useMemo, useState }
export { jsx, jsxs } from 'react/jsx-runtime'

export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar-nav'
export const PALETTE_AREA = 'palette'

export const host = {
  navigate() {},
  onEvent() {
    return () => {}
  },
  notify() {}
}

export const queryClient = {
  invalidateQueries() {}
}

export function useQuery({ queryFn }) {
  const fn = useRef(queryFn)
  fn.current = queryFn
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const refetch = async () => {
    try {
      const next = await fn.current()
      setData(next)
      setError(null)
      return next
    } catch (err) {
      setError(err)
      return null
    }
  }
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const next = await fn.current()
        if (alive) {
          setData(next)
          setError(null)
        }
      } catch (err) {
        if (alive) setError(err)
      }
    }
    tick()
    const timer = setInterval(tick, 1200)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  return { data, isLoading: data === null && error === null, error, refetch }
}

export function Button({ children, onClick, disabled, variant, size, ...rest }) {
  return React.createElement(
    'button',
    {
      type: 'button',
      onClick,
      disabled,
      'data-variant': variant,
      'data-size': size,
      style: {
        padding: size === 'xs' ? '3px 7px' : '5px 9px',
        border: '1px solid rgba(255,255,255,.18)',
        background: variant === 'default' ? '#2d2b25' : 'transparent',
        color: '#e9e3d6',
        fontFamily: 'var(--font-mono, monospace)',
        fontSize: '11px',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.5 : 1
      },
      ...rest
    },
    children
  )
}
