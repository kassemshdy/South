import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { useEffect, useRef, useState } from 'react'

import type { Pin } from '@/features/map/types'

/** Roughly the South, for a map with no pin yet. */
const SOUTH: L.LatLngExpression = [33.3, 35.4]

/**
 * A pin drawn in SVG rather than Leaflet's default marker images, whose
 * paths break once the bundler renames them -- and it takes the brand colour.
 */
const PIN_ICON = L.divIcon({
  className: '',
  iconSize: [32, 40],
  iconAnchor: [16, 40],
  html:
    '<svg width="32" height="40" viewBox="0 0 32 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
    '<path d="M16 0C7.2 0 0 7 0 15.7 0 27.5 16 40 16 40s16-12.5 16-24.3C32 7 24.8 0 16 0z" fill="#1f4d3a"/>' +
    '<circle cx="16" cy="15.5" r="6" fill="#fff"/></svg>',
})

export interface LeafletMapProps {
  value: Pin | null
  /** Absent for a map that only shows a pin. */
  onChange?: (pin: Pin) => void
  label: string
  className?: string
}

/**
 * OpenStreetMap through Leaflet: free, with no key and no account, which is
 * what the owners chose over Google's paid maps. Loaded only on the pages
 * that draw a map (see MapView), so the rest of the site never downloads it.
 *
 * Editable when given `onChange`: a tap drops the pin, and the pin can be
 * dragged. Laid out left-to-right whatever the page's direction, because a
 * map's controls and attribution assume it.
 */
export default function LeafletMap({ value, onChange, label, className }: LeafletMapProps) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const marker = useRef<L.Marker | null>(null)
  const changeRef = useRef(onChange)
  changeRef.current = onChange
  const editable = Boolean(onChange)
  // Set once Leaflet is listening. The container is on screen a moment
  // before that, and a tap in between would be lost -- which is how a test
  // that clicks fast enough once failed to drop a pin at all.
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, {
      center: value ? [value.lat, value.lng] : SOUTH,
      zoom: value ? 14 : 9,
      scrollWheelZoom: false,
    })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance)
    if (editable) {
      instance.on('click', (event: L.LeafletMouseEvent) => {
        changeRef.current?.({ lat: event.latlng.lat, lng: event.latlng.lng })
      })
    }
    map.current = instance
    setReady(true)
    return () => {
      setReady(false)
      instance.remove()
      map.current = null
      marker.current = null
    }
    // Built once; the pin is kept in step by the effect below.
  }, [])

  useEffect(() => {
    const instance = map.current
    if (!instance) return
    if (!value) {
      marker.current?.remove()
      marker.current = null
      return
    }
    const at: L.LatLngExpression = [value.lat, value.lng]
    if (marker.current) {
      marker.current.setLatLng(at)
    } else {
      const created = L.marker(at, { icon: PIN_ICON, draggable: editable, keyboard: false })
      if (editable) {
        created.on('dragend', () => {
          const moved = created.getLatLng()
          changeRef.current?.({ lat: moved.lat, lng: moved.lng })
        })
      }
      marker.current = created.addTo(instance)
    }
    if (!instance.getBounds().contains(at)) instance.setView(at, Math.max(instance.getZoom(), 13))
  }, [value, editable])

  return (
    <div
      ref={container}
      dir="ltr"
      role="region"
      aria-label={label}
      data-ready={ready ? 'true' : 'false'}
      className={className ?? 'h-64 w-full overflow-hidden rounded-xl border-2 border-ink-100'}
    />
  )
}
