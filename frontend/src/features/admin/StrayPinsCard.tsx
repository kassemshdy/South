import { useQuery } from '@tanstack/react-query'
import { MapPinOff } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { useT } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * Listings whose map pin falls outside Lebanon -- saved before pins were
 * checked -- and so shown on no public map (the owners' report, 9 Nov 2026:
 * a shop pinned across the southern border). Each links to the listing's
 * admin page, where the place card moves the pin. Nothing at all when
 * every pin is inside the border.
 */
export function StrayPinsCard() {
  const t = useT()
  const pins = useQuery({ queryKey: queryKeys.adminStrayPins, queryFn: adminApi.strayPins })
  if (!pins.data?.length) return null

  return (
    <Card className="border-clay-200 bg-clay-50/40">
      <CardBody className="space-y-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <MapPinOff className="h-5 w-5 text-clay-600" aria-hidden="true" />
          {t('admin.strayPinsHeading', { count: pins.data.length })}
        </h2>
        <p className="text-sm text-ink-500">{t('admin.strayPinsHint')}</p>
        <ul className="divide-y divide-ink-100 rounded-xl border border-ink-100 bg-white">
          {pins.data.map((pin) => (
            <li key={pin.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <Link
                to={pin.kind === 'business' ? `/admin/businesses/${pin.id}` : `/admin/talent/${pin.id}`}
                className="font-semibold hover:text-brand-700"
                dir="auto"
              >
                {pin.name}
              </Link>
              <span className="text-sm text-ink-500">
                {[
                  t(pin.kind === 'business' ? 'admin.strayPinShop' : 'admin.strayPinService'),
                  pin.town,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}
