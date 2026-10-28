import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { useToast } from '@/components/ui/Toast'
import { MapPinField } from '@/features/map/MapPinField'
import { pinOf, type Pin } from '@/features/map/types'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'

/**
 * Where a listing is -- its town and map pin -- shown to the reviewer and
 * corrected on the owner's behalf: for a pin put across the border, or a
 * town that is not where the shop or service is (the owners' tickets,
 * 28 Oct 2026). The map refuses a pin outside Lebanon, as the API does.
 */
export function AdminPlaceCard({
  locationId,
  latitude,
  longitude,
  onSave,
  onSaved,
}: {
  locationId: string | null
  latitude: number | null
  longitude: number | null
  onSave: (place: { location_id: string; latitude: number; longitude: number }) => Promise<unknown>
  onSaved: () => void
}) {
  const t = useT()
  const toast = useToast()
  const { groups } = useLocationGroups()
  const [town, setTown] = useState(locationId ?? '')
  const [pin, setPin] = useState<Pin | null>(pinOf(latitude, longitude))

  const unchanged =
    town === (locationId ?? '') && pin?.lat === latitude && pin?.lng === longitude

  const save = useMutation({
    mutationFn: () => onSave({ location_id: town, latitude: pin!.lat, longitude: pin!.lng }),
    onSuccess: () => {
      onSaved()
      toast.success(t('admin.correctionSaved'))
    },
    onError: (error) =>
      toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-bold">{t('admin.placeTitle')}</h2>
      </CardHeader>
      <CardBody className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-semibold" htmlFor="admin-place-town">
            {t('form.area')}
          </label>
          <LocationCombobox id="admin-place-town" value={town} onChange={setTown} groups={groups} />
        </div>
        <MapPinField value={pin} onChange={setPin} />
        <Button
          size="sm"
          disabled={unchanged || !town || !pin}
          loading={save.isPending}
          onClick={() => save.mutate()}
        >
          {t('common.save')}
        </Button>
      </CardBody>
    </Card>
  )
}
