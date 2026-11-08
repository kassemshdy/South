import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useMemo, useState } from 'react'

import { Card, CardBody } from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/States'
import type { ClusterPoint } from '@/features/map/ClusterMap'
import { useT } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { STATUS_KEYS } from '@/utils/format'

const ClusterMap = lazy(() => import('@/features/map/ClusterMap'))

/** Shops in the brand green, service profiles in blue. */
const COLORS = { business: '#1f4d3a', service: '#2563eb' } as const

/**
 * Every pinned shop and service profile on one map, clustered (the owners'
 * request, 8 Nov 2026). Staff see each exact pin, a service provider's too,
 * which the public page shows only as an area. A pin not yet published is
 * hollow; a tap opens its admin page.
 */
export function ListingsMapCard() {
  const t = useT()
  const [shops, setShops] = useState(true)
  const [services, setServices] = useState(true)
  const [approvedOnly, setApprovedOnly] = useState(false)
  const data = useQuery({ queryKey: queryKeys.adminListingsMap, queryFn: adminApi.listingsMap })

  const all = data.data ?? []
  const shopCount = all.filter((point) => point.kind === 'business').length
  const serviceCount = all.length - shopCount
  const points = useMemo<ClusterPoint[]>(
    () =>
      (data.data ?? [])
        .filter((point) => (point.kind === 'business' ? shops : services))
        .filter((point) => !approvedOnly || point.status === 'APPROVED')
        .map((point) => ({
          id: `${point.kind}-${point.id}`,
          lat: point.latitude,
          lng: point.longitude,
          color: COLORS[point.kind],
          hollow: point.status !== 'APPROVED',
          title: point.name,
          subtitle: [point.category, t(STATUS_KEYS[point.status])].filter(Boolean).join(' · '),
          href:
            point.kind === 'business'
              ? `/admin/businesses/${point.id}`
              : `/admin/talent/${point.id}`,
          linkLabel: t('admin.mapOpen'),
        })),
    [data.data, shops, services, approvedOnly, t],
  )

  const toggle = 'inline-flex items-center gap-2 text-sm font-semibold text-ink-700'
  return (
    <Card>
      <CardBody className="space-y-4">
        <div>
          <h2 className="text-xl font-bold">{t('admin.mapTitle')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('admin.mapHint')}</p>
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <label className={toggle}>
            <input type="checkbox" checked={shops} onChange={(e) => setShops(e.target.checked)} />
            <span className="h-3 w-3 rounded-full" style={{ background: COLORS.business }} />
            {t('admin.mapShops', { count: shopCount })}
          </label>
          <label className={toggle}>
            <input
              type="checkbox"
              checked={services}
              onChange={(e) => setServices(e.target.checked)}
            />
            <span className="h-3 w-3 rounded-full" style={{ background: COLORS.service }} />
            {t('admin.mapServices', { count: serviceCount })}
          </label>
          <label className={toggle}>
            <input
              type="checkbox"
              checked={approvedOnly}
              onChange={(e) => setApprovedOnly(e.target.checked)}
            />
            {t('admin.mapApprovedOnly')}
          </label>
        </div>
        {data.isError ? (
          <ErrorState error={data.error} onRetry={() => void data.refetch()} />
        ) : (
          <Suspense fallback={<div className="h-[28rem] rounded-xl bg-sand-50" aria-hidden="true" />}>
            <ClusterMap points={points} label={t('admin.mapLabel')} />
          </Suspense>
        )}
      </CardBody>
    </Card>
  )
}
