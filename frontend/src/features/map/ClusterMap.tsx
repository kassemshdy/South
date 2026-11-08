import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'

import L from 'leaflet'
import 'leaflet.markercluster'
import { useEffect, useRef } from 'react'

/** One pin on a clustered map. */
export interface ClusterPoint {
  id: string
  lat: number
  lng: number
  /** Fill colour of the pin. */
  color: string
  /** A hollow pin, for a listing not (yet) public. */
  hollow?: boolean
  /** Shown in the popup, escaped. */
  title: string
  subtitle?: string
  href?: string
  linkLabel?: string
}

export interface ClusterMapProps {
  points: ClusterPoint[]
  label: string
  className?: string
}

const SOUTH: L.LatLngExpression = [33.3, 35.4]

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`)
}

function pinIcon(color: string, hollow: boolean): L.DivIcon {
  const fill = hollow ? '#ffffff' : color
  const dot = hollow ? color : '#ffffff'
  return L.divIcon({
    className: '',
    iconSize: [26, 32],
    iconAnchor: [13, 32],
    popupAnchor: [0, -28],
    html:
      '<svg width="26" height="32" viewBox="0 0 32 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
      `<path d="M16 0C7.2 0 0 7 0 15.7 0 27.5 16 40 16 40s16-12.5 16-24.3C32 7 24.8 0 16 0z" fill="${fill}" stroke="${color}" stroke-width="3"/>` +
      `<circle cx="16" cy="15.5" r="6" fill="${dot}"/></svg>`,
  })
}

/**
 * Many pins on one map, grouped into numbered clusters that split as you
 * zoom in (Leaflet.markercluster). OpenStreetMap like every map here, and
 * its own chunk: only the page that draws it downloads it.
 */
export default function ClusterMap({ points, label, className }: ClusterMapProps) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layer = useRef<L.MarkerClusterGroup | null>(null)

  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { center: SOUTH, zoom: 9, scrollWheelZoom: false })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance)
    const group = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 50 })
    instance.addLayer(group)
    map.current = instance
    layer.current = group
    return () => {
      instance.remove()
      map.current = null
      layer.current = null
    }
  }, [])

  useEffect(() => {
    const instance = map.current
    const group = layer.current
    if (!instance || !group) return
    group.clearLayers()
    const markers = points.map((point) => {
      const lines = [`<strong dir="auto">${escapeHtml(point.title)}</strong>`]
      if (point.subtitle) lines.push(`<span dir="auto">${escapeHtml(point.subtitle)}</span>`)
      if (point.href) {
        lines.push(
          `<a href="${escapeHtml(point.href)}">${escapeHtml(point.linkLabel ?? point.href)}</a>`,
        )
      }
      return L.marker([point.lat, point.lng], {
        icon: pinIcon(point.color, Boolean(point.hollow)),
        keyboard: false,
      }).bindPopup(`<div dir="rtl" style="display:grid;gap:4px">${lines.join('')}</div>`)
    })
    group.addLayers(markers)
    if (markers.length > 0) {
      instance.fitBounds(group.getBounds(), { padding: [24, 24], maxZoom: 13 })
    }
  }, [points])

  return (
    <div
      ref={container}
      dir="ltr"
      role="region"
      aria-label={label}
      className={`isolate ${className ?? 'h-[28rem] w-full overflow-hidden rounded-xl border-2 border-ink-100'}`}
    />
  )
}
