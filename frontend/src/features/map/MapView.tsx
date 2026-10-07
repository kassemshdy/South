import { lazy, Suspense } from 'react'

import type { LeafletMapProps } from '@/features/map/LeafletMap'

const LeafletMap = lazy(() => import('@/features/map/LeafletMap'))

/**
 * The map, loaded on first use: Leaflet and its stylesheet are a separate
 * chunk that only the pages drawing a map ever fetch.
 */
export function MapView(props: LeafletMapProps) {
  return (
    <Suspense
      fallback={
        <div
          className={props.className ?? 'h-64 w-full rounded-xl border-2 border-ink-100 bg-sand-50'}
          aria-hidden="true"
        />
      }
    >
      <LeafletMap {...props} />
    </Suspense>
  )
}
