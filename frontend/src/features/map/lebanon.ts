import border from '@/features/map/lebanonBorder.json'

/**
 * Lebanon's border, the same outline the API checks a pin against
 * (backend/app/core/pins.py, which also tests that the two files match):
 * land borders to about 300 m, the coast moved about 2 km out to sea.
 * [longitude, latitude] pairs.
 */
const RING = border.ring as [number, number][]

/** The outline as Leaflet wants it, [latitude, longitude]. */
export const LEBANON_OUTLINE: [number, number][] = RING.map(([lng, lat]) => [lat, lng])

/** Even-odd ray casting, as on the server. */
export function insideLebanon(lat: number, lng: number): boolean {
  let inside = false
  for (let i = 0, j = RING.length - 1; i < RING.length; j = i++) {
    const [xi, yi] = RING[i]!
    const [xj, yj] = RING[j]!
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      inside = !inside
    }
  }
  return inside
}
