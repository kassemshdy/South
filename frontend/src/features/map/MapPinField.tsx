import { LocateFixed } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { useToast } from '@/components/ui/Toast'
import { MapView } from '@/features/map/MapView'
import type { Pin } from '@/features/map/types'
import { useT } from '@/i18n'

/** About a metre: more than any seller needs, and a tidy number to store. */
function tidy(pin: Pin): Pin {
  return { lat: Math.round(pin.lat * 1e5) / 1e5, lng: Math.round(pin.lng * 1e5) / 1e5 }
}

/**
 * Where a seller is, as a pin they drop on the map -- required of every
 * seller, at the owners' request, and published on the listing page. The
 * town is enough, which the hint says, because a home business should not
 * feel it has to point at its front door.
 *
 * "Use my location" is for the seller standing in their shop; anyone else
 * taps the map. The browser is asked only when that button is pressed.
 */
export function MapPinField({
  value,
  onChange,
  error,
}: {
  value: Pin | null
  onChange: (pin: Pin) => void
  error?: string | undefined
}) {
  const t = useT()
  const toast = useToast()
  const [locating, setLocating] = useState(false)

  const useMine = () => {
    if (!('geolocation' in navigator)) {
      toast.error(t('directory.nearestUnavailable'))
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocating(false)
        onChange(tidy({ lat: coords.latitude, lng: coords.longitude }))
      },
      () => {
        setLocating(false)
        toast.error(t('directory.nearestUnavailable'))
      },
      { timeout: 15_000 },
    )
  }

  return (
    <Field label={t('form.mapPinLabel')} required error={error} hint={t('form.mapPinHint')}>
      {(props) => (
        <div id={props.id} aria-describedby={props['aria-describedby']} className="space-y-2">
          <MapView
            value={value}
            onChange={(pin) => onChange(tidy(pin))}
            label={t('form.mapPinLabel')}
            className={
              error
                ? 'h-64 w-full overflow-hidden rounded-xl border-2 border-clay-500'
                : undefined
            }
          />
          <Button type="button" variant="outline" size="sm" loading={locating} onClick={useMine}>
            <LocateFixed className="h-4 w-4" aria-hidden="true" />
            {t('form.mapPinUseMine')}
          </Button>
        </div>
      )}
    </Field>
  )
}
