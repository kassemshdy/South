import { MapView } from '@/features/map/MapView'
import type { Pin } from '@/features/map/types'
import { useT } from '@/i18n'

/** The seller's pin on a listing page, read-only. Nothing when there is none. */
export function ListingMap({ pin }: { pin: Pin | null }) {
  const t = useT()
  if (!pin) return null
  return (
    <MapView
      value={pin}
      label={t('form.mapPinLabel')}
      className="h-48 w-full overflow-hidden rounded-xl border border-ink-100"
    />
  )
}
