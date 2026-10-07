/** A point on the map, as the API stores it: latitude and longitude. */
export interface Pin {
  lat: number
  lng: number
}

export function pinOf(latitude: number | null | undefined, longitude: number | null | undefined): Pin | null {
  return latitude != null && longitude != null ? { lat: latitude, lng: longitude } : null
}

/** A link that opens the pin in Google Maps -- free, and on most phones. */
export function googleMapsHref(pin: Pin): string {
  return `https://www.google.com/maps/search/?api=1&query=${pin.lat},${pin.lng}`
}
