import { useCallback, useEffect, useState } from 'react'

import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'

export interface Position {
  lat: number
  lng: number
}

/**
 * About a kilometre. Enough to order a directory by distance, and the most a
 * request ever carries: the position goes to the API in a query string, and
 * a rounded one says which part of a town someone is in, not which house.
 */
function rounded(value: number): number {
  return Math.round(value * 100) / 100
}

const CACHE_KEY = 'south.position'

function cached(): Position | null {
  try {
    const raw = window.sessionStorage.getItem(CACHE_KEY)
    return raw ? (JSON.parse(raw) as Position) : null
  } catch {
    return null
  }
}

function locate(onDone: (position: Position | null) => void) {
  if (!('geolocation' in navigator)) {
    onDone(null)
    return
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const position = { lat: rounded(coords.latitude), lng: rounded(coords.longitude) }
      try {
        window.sessionStorage.setItem(CACHE_KEY, JSON.stringify(position))
      } catch {
        /* private mode: asked again next page, nothing worse */
      }
      onDone(position)
    },
    () => onDone(null),
    { maximumAge: 10 * 60_000, timeout: 15_000 },
  )
}

/**
 * The directories' sort order, with "nearest" as the default for a visitor
 * who has already let the site know where they are.
 *
 * The browser is asked only when someone chooses nearest, never on arrival:
 * a permission prompt on page load is answered "no" out of reflex, and then
 * cannot be asked again. Once granted -- now or on an earlier visit -- the
 * directories open nearest-first, which is what the owners asked for, while
 * an order chosen explicitly in the URL still wins.
 *
 * The position lives in this tab's session storage and in the request, never
 * in the page URL: a link someone shares should not carry where they were.
 */
export function useNearestSort<S extends string>(
  chosen: S | 'nearest' | null,
  setSort: (sort: S | 'nearest') => void,
  fallback: S,
) {
  const t = useT()
  const toast = useToast()
  const [position, setPosition] = useState<Position | null>(cached)
  const [locating, setLocating] = useState(false)

  // Already granted, on this visit or an earlier one: locate silently, which
  // makes nearest the default without a prompt.
  useEffect(() => {
    if (position || !navigator.permissions?.query) return
    let active = true
    navigator.permissions
      .query({ name: 'geolocation' })
      .then((status) => {
        if (active && status.state === 'granted') locate((found) => active && setPosition(found))
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [position])

  const sort: S | 'nearest' = chosen ?? (position ? 'nearest' : fallback)

  const choose = useCallback(
    (option: S | 'nearest') => {
      setSort(option)
      if (option !== 'nearest' || position) return
      setLocating(true)
      locate((found) => {
        setLocating(false)
        setPosition(found)
        if (!found) toast.error(t('directory.nearestUnavailable'))
      })
    },
    [position, setSort, t, toast],
  )

  return {
    sort,
    choose,
    locating,
    /** Sent with the search only while sorting by distance. */
    near: sort === 'nearest' && position ? position : null,
  }
}
