import { useQuery } from '@tanstack/react-query'
import { MapPinOff } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { useT } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { StrayPin } from '@/types/api'

/**
 * Map pins a person should look at (the owners' reports, 9 Nov 2026):
 * - outside Lebanon -- saved before pins were checked, and shown on no
 *   public map until moved;
 * - inside it but far from the other pins of their district -- often a
 *   displaced owner pinned where they live now, so they stay on the map
 *   and staff decide.
 * Each links to the listing's admin page, where the place card moves the
 * pin. Nothing at all when every pin looks right.
 */
export function StrayPinsCard() {
  const t = useT()
  const pins = useQuery({ queryKey: queryKeys.adminStrayPins, queryFn: adminApi.strayPins })
  if (!pins.data?.length) return null
  const outside = pins.data.filter((pin) => pin.reason === 'outside')
  const far = pins.data.filter((pin) => pin.reason === 'far')

  return (
    <Card className="border-clay-200 bg-clay-50/40">
      <CardBody className="space-y-4">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <MapPinOff className="h-5 w-5 text-clay-600" aria-hidden="true" />
          {t('admin.strayPinsTitle')}
        </h2>
        {outside.length > 0 ? (
          <PinGroup
            heading={t('admin.strayPinsHeading', { count: outside.length })}
            hint={t('admin.strayPinsHint')}
            pins={outside}
          />
        ) : null}
        {far.length > 0 ? (
          <PinGroup
            heading={t('admin.farPinsHeading', { count: far.length })}
            hint={t('admin.farPinsHint')}
            pins={far}
          />
        ) : null}
      </CardBody>
    </Card>
  )
}

function PinGroup({ heading, hint, pins }: { heading: string; hint: string; pins: StrayPin[] }) {
  const t = useT()
  return (
    <section className="space-y-2">
      <h3 className="font-bold">{heading}</h3>
      <p className="text-sm text-ink-500">{hint}</p>
      <ul className="divide-y divide-ink-100 rounded-xl border border-ink-100 bg-white">
        {pins.map((pin) => (
          <li key={pin.id} className="flex flex-wrap items-center justify-between gap-x-3 px-4 py-2.5">
            <Link
              to={pin.kind === 'business' ? `/admin/businesses/${pin.id}` : `/admin/talent/${pin.id}`}
              className="font-semibold hover:text-brand-700"
              dir="auto"
            >
              {pin.name}
            </Link>
            <span className="ltr-nums text-sm text-ink-500">
              {[
                t(pin.kind === 'business' ? 'admin.strayPinShop' : 'admin.strayPinService'),
                pin.town,
                pin.km_from_district != null
                  ? t('admin.farPinKm', { count: pin.km_from_district })
                  : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
