import { useQuery } from '@tanstack/react-query'
import { Link2 } from 'lucide-react'
import { lazy, Suspense, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import type { ClusterPoint } from '@/features/map/ClusterMap'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { southMapApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { MapListing } from '@/types/api'
import { matchesSearch } from '@/utils/search'

const ClusterMap = lazy(() => import('@/features/map/ClusterMap'))

const COLORS = { business: '#1f4d3a', service: '#2563eb' } as const
/** From the southern border up to Beirut: what the page opens on. */
const SOUTH_TO_BEIRUT: [[number, number], [number, number]] = [
  [33.06, 35.1],
  [33.93, 35.75],
]
type Kind = 'all' | MapListing['kind']

/**
 * The South on a map, with a chart of how many shops and service providers
 * each district has, from the border up to Beirut (the owners' request,
 * 8 Nov 2026). Every filter lives in the address, so a filtered view is a
 * link to share. Service providers are at the area of their town (the API
 * rounds their pin), as on their own pages.
 */
export function SouthMapPage() {
  const t = useT()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const kind = (params.get('kind') as Kind | null) ?? 'all'
  const category = params.get('category') ?? ''
  const district = params.get('district') ?? ''
  const q = params.get('q') ?? ''

  useSeo({
    title: `${t('southMap.title')} | ${t('app.name')}`,
    description: t('southMap.subtitle'),
    canonicalPath: '/map',
  })

  const data = useQuery({ queryKey: queryKeys.southMap, queryFn: southMapApi.listings })
  const all = data.data ?? []

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const ofKind = all.filter((row) => kind === 'all' || row.kind === kind)
  const categories = useMemo(() => {
    const seen = new Map<string, string>()
    for (const row of ofKind) if (row.category_slug && row.category) seen.set(row.category_slug, row.category)
    return [...seen].sort((a, b) => a[1].localeCompare(b[1], 'ar'))
  }, [ofKind])
  // Everything but the district: the chart shows every district for the
  // other filters, so a bar can be picked and unpicked.
  const beforeDistrict = ofKind.filter(
    (row) =>
      (!category || row.category_slug === category) && (!q || matchesSearch(q, row.name, row.town)),
  )
  const shown = beforeDistrict.filter((row) => !district || (row.district ?? '') === district)

  // Districts from south to north: ordered by the mean latitude of what is in them.
  const bars = useMemo(() => {
    const groups = new Map<string, { shops: number; services: number; lat: number; n: number }>()
    for (const row of beforeDistrict) {
      const key = row.district ?? ''
      const g = groups.get(key) ?? { shops: 0, services: 0, lat: 0, n: 0 }
      if (row.kind === 'business') g.shops += 1
      else g.services += 1
      g.lat += row.latitude
      g.n += 1
      groups.set(key, g)
    }
    return [...groups]
      .map(([name, g]) => ({ name, shops: g.shops, services: g.services, lat: g.lat / g.n }))
      .sort((a, b) => a.lat - b.lat)
  }, [beforeDistrict])
  const widest = Math.max(1, ...bars.map((bar) => bar.shops + bar.services))

  const points = useMemo<ClusterPoint[]>(
    () =>
      shown.map((row) => ({
        id: `${row.kind}-${row.slug}`,
        lat: row.latitude,
        lng: row.longitude,
        color: COLORS[row.kind],
        hollow: row.kind === 'service',
        title: row.name,
        subtitle: [row.category, row.town].filter(Boolean).join(' · '),
        href: row.kind === 'business' ? `/business/${encodeURIComponent(row.slug)}` : `/talent/${encodeURIComponent(row.slug)}`,
        linkLabel: t('southMap.open'),
      })),
    [shown, t],
  )

  const shops = shown.filter((row) => row.kind === 'business').length
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      toast.success(t('southMap.copied'))
    } catch {
      // The address bar holds the same link.
    }
  }

  const pill = (active: boolean) =>
    `rounded-full border-2 px-4 py-1.5 text-sm font-semibold transition-colors ${
      active ? 'border-brand-700 bg-brand-700 text-white' : 'border-ink-100 bg-white text-ink-700 hover:border-brand-300'
    }`

  return (
    <div className="container-page space-y-6 py-10">
      <header>
        <h1 className="text-3xl">{t('southMap.title')}</h1>
        <p className="mt-2 max-w-3xl text-ink-500">{t('southMap.subtitle')}</p>
      </header>

      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap gap-2" role="group">
            {(['all', 'business', 'service'] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={kind === value}
                className={pill(kind === value)}
                onClick={() => set('kind', value === 'all' ? '' : value)}
              >
                {t(value === 'all' ? 'southMap.kindAll' : value === 'business' ? 'southMap.kindShops' : 'southMap.kindServices')}
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <select
              aria-label={t('southMap.category')}
              className="rounded-xl border-2 border-ink-100 bg-white px-3 py-2.5"
              value={category}
              onChange={(e) => set('category', e.target.value)}
            >
              <option value="">{t('southMap.allCategories')}</option>
              {categories.map(([slug, name]) => (
                <option key={slug} value={slug}>
                  {name}
                </option>
              ))}
            </select>
            <select
              aria-label={t('southMap.district')}
              className="rounded-xl border-2 border-ink-100 bg-white px-3 py-2.5"
              value={district}
              onChange={(e) => set('district', e.target.value)}
            >
              <option value="">{t('southMap.allDistricts')}</option>
              {bars.map((bar) => (
                <option key={bar.name} value={bar.name}>
                  {bar.name || t('southMap.noDistrict')}
                </option>
              ))}
            </select>
            <Input
              type="search"
              value={q}
              placeholder={t('southMap.search')}
              aria-label={t('southMap.search')}
              onChange={(e) => set('q', e.target.value)}
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="font-semibold text-ink-700">
              {t('southMap.count', { shops, services: shown.length - shops })}
            </p>
            <div className="flex flex-wrap gap-2">
              {params.toString() ? (
                <Button size="sm" variant="ghost" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                  {t('southMap.reset')}
                </Button>
              ) : null}
              <Button size="sm" variant="secondary" onClick={() => void copy()}>
                <Link2 className="h-4 w-4" aria-hidden="true" />
                {t('southMap.copyLink')}
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      {data.isError ? (
        <ErrorState error={data.error} onRetry={() => void data.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Suspense fallback={<div className="h-[34rem] rounded-xl bg-sand-50" aria-hidden="true" />}>
              <ClusterMap
                points={points}
                label={t('southMap.mapLabel')}
                frame={district || category || q ? undefined : SOUTH_TO_BEIRUT}
                className="h-[34rem] w-full overflow-hidden rounded-xl border-2 border-ink-100"
              />
            </Suspense>
            <p className="mt-2 text-xs text-ink-500">{t('southMap.areaNote')}</p>
          </div>

          <Card>
            <CardBody className="space-y-3">
              <h2 className="font-bold">{t('southMap.chartTitle')}</h2>
              <div className="flex gap-4 text-xs text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-sm" style={{ background: COLORS.business }} />
                  {t('southMap.kindShops')}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-sm" style={{ background: COLORS.service }} />
                  {t('southMap.kindServices')}
                </span>
              </div>
              {bars.length === 0 ? (
                <p className="text-sm text-ink-500">{t('southMap.empty')}</p>
              ) : (
                <ul className="space-y-1.5">
                  {[...bars].reverse().map((bar) => {
                    const active = district === bar.name
                    return (
                      <li key={bar.name}>
                        <button
                          type="button"
                          aria-pressed={active}
                          onClick={() => set('district', active ? '' : bar.name)}
                          className={`w-full rounded-lg px-2 py-1.5 text-start transition-colors ${
                            active ? 'bg-sand-100' : 'hover:bg-sand-50'
                          }`}
                        >
                          <span className="flex justify-between text-sm">
                            <span className="font-semibold text-ink-800">{bar.name || t('southMap.noDistrict')}</span>
                            <span className="ltr-nums text-ink-500">{bar.shops + bar.services}</span>
                          </span>
                          <span className="mt-1 flex h-3 overflow-hidden rounded-full bg-ink-50">
                            <span style={{ width: `${(bar.shops / widest) * 100}%`, background: COLORS.business }} />
                            <span style={{ width: `${(bar.services / widest) * 100}%`, background: COLORS.service }} />
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  )
}
