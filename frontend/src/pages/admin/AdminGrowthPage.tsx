import { useQuery } from '@tanstack/react-query'
import { FileDown, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useI18n, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { GrowthLever, GrowthReport, GrowthShopLine } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDateTime } from '@/utils/format'

/**
 * The growth plan's analysis, read off the live data.
 *
 * Alex Hormozi's value equation, with each of its four levers given the
 * real numbers that move it, and the next steps the numbers call for. The
 * server computes it on every request and nothing is cached here
 * (`staleTime: 0`), so opening the page is recalculating it.
 *
 * "Export PDF" is the browser's own print dialog: the site's header, footer
 * and the admin menu are hidden when printing, so the saved PDF is the
 * report alone, charts included, since they are inline SVG.
 */
const LEVERS: GrowthLever[] = ['outcome', 'likelihood', 'time', 'effort']

export function AdminGrowthPage() {
  const { t, locale } = useI18n()
  const report = useQuery({
    queryKey: queryKeys.adminGrowthReport,
    queryFn: adminApi.growthReport,
    staleTime: 0,
    refetchOnMount: 'always',
  })

  return (
    <div className="space-y-8 print:space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl">{t('growth.title')}</h1>
          <p className="mt-2 text-ink-500">{t('growth.subtitle')}</p>
          {report.data ? (
            <p className="mt-1 text-sm text-ink-500">
              {t('growth.generatedAt', { time: formatDateTime(report.data.generated_at, locale) })}
            </p>
          ) : null}
        </div>
        <div className="flex gap-2 print:hidden">
          <Button
            variant="outline"
            size="sm"
            loading={report.isFetching}
            onClick={() => void report.refetch()}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            {t('growth.refresh')}
          </Button>
          <Button size="sm" disabled={!report.data} onClick={() => window.print()}>
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {t('growth.exportPdf')}
          </Button>
        </div>
      </header>

      {report.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-40 rounded-2xl" />
          ))}
        </div>
      ) : report.isError ? (
        <ErrorState error={report.error} onRetry={() => void report.refetch()} />
      ) : report.data ? (
        <Report data={report.data} />
      ) : null}
    </div>
  )
}

function Report({ data }: { data: GrowthReport }) {
  const { t } = useI18n()
  const share = data.approved_shops
    ? Math.round((data.shops_with_order_30d / data.approved_shops) * 100)
    : 0

  const kpis: { labelKey: TranslationKey; value: string }[] = [
    { labelKey: 'growth.kpiOrders7', value: String(data.orders_7d) },
    { labelKey: 'growth.kpiOrders30', value: String(data.orders_30d) },
    { labelKey: 'growth.kpiRequests30', value: String(data.service_requests_30d) },
    { labelKey: 'growth.kpiViews30', value: String(data.views_30d) },
    {
      labelKey: 'growth.kpiPerThousand',
      value: data.orders_per_1000_views === null ? '—' : String(data.orders_per_1000_views),
    },
    { labelKey: 'growth.kpiShops', value: String(data.approved_shops) },
    { labelKey: 'growth.kpiTalents', value: String(data.approved_talents) },
    { labelKey: 'growth.kpiProducts', value: String(data.public_products) },
  ]

  const leverMetric: Record<GrowthLever, string> = {
    outcome: t('growth.metric.outcome', {
      orders: data.orders_30d,
      requests: data.service_requests_30d,
    }),
    likelihood: t('growth.metric.likelihood', {
      share,
      testimonials: data.approved_testimonials,
    }),
    time:
      data.median_approval_hours === null
        ? t('growth.metric.timeNone', { late: data.pending_over_48h })
        : t('growth.metric.time', {
            hours: Math.round(data.median_approval_hours),
            late: data.pending_over_48h,
          }),
    effort: t('growth.metric.effort', {
      thin: data.thin_catalogue_shops,
      logo: data.shops_without_logo,
    }),
  }

  return (
    <>
      {/* The plan's constraint first: did sellers get customers? */}
      <section className="rounded-3xl bg-brand-900 p-6 text-white print:break-inside-avoid sm:p-8">
        <p className="text-sm font-semibold text-wheat-300">{t('growth.questionLabel')}</p>
        <p className="mt-1 text-xl font-bold sm:text-2xl">{t('growth.question')}</p>
        <p className="mt-4 text-4xl font-bold sm:text-5xl">
          {t('growth.questionAnswer', {
            count: data.shops_with_order_7d,
            total: data.approved_shops,
          })}
        </p>
        <p className="mt-2 text-white/80">
          {t('growth.question30', { count: data.shops_with_order_30d })}
        </p>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4 print:break-inside-avoid">
        {kpis.map((kpi) => (
          <Card key={kpi.labelKey}>
            <CardBody className="p-4">
              <p className="text-2xl font-bold ltr-nums text-ink-900">{kpi.value}</p>
              <p className="mt-1 text-sm text-ink-500">{t(kpi.labelKey)}</p>
            </CardBody>
          </Card>
        ))}
      </section>

      <section className="space-y-4 print:break-inside-avoid">
        <div>
          <h2 className="text-xl">{t('growth.weeklyHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('growth.weeklyHint')}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 print:grid-cols-2">
          <WeeklyBars
            label={t('growth.chartOrders')}
            values={data.weekly.orders}
            weeks={data.week_starts}
            barClass="fill-brand-700"
          />
          <WeeklyBars
            label={t('growth.chartViews')}
            values={data.weekly.views}
            weeks={data.week_starts}
            barClass="fill-sea-500"
          />
          <WeeklyBars
            label={t('growth.chartSellers')}
            values={data.weekly.new_sellers}
            weeks={data.week_starts}
            barClass="fill-clay-500"
          />
          <WeeklyBars
            label={t('growth.chartProducts')}
            values={data.weekly.new_products}
            weeks={data.week_starts}
            barClass="fill-wheat-500"
          />
        </div>
      </section>

      <HealthBar health={data.health} total={data.approved_shops} />

      <section className="space-y-4 print:break-inside-avoid">
        <div>
          <h2 className="text-xl">{t('growth.equationHeading')}</h2>
          <p className="mt-2 rounded-xl border-2 border-dashed border-wheat-300 p-3 text-center font-semibold text-ink-900">
            {t('growth.equation')}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 print:grid-cols-2">
          {LEVERS.map((lever) => (
            <Card key={lever}>
              <CardBody className="p-4">
                <p className="font-bold text-brand-800">{t(`growth.lever.${lever}`)}</p>
                <p className="text-sm text-ink-500">{t(`growth.leverHint.${lever}`)}</p>
                <p className="mt-2 font-semibold text-ink-900">{leverMetric[lever]}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-3 print:break-inside-avoid">
        <h2 className="text-xl">{t('growth.recsHeading')}</h2>
        <ol className="space-y-2">
          {data.recommendations.map((rec) => (
            <li
              key={rec.key}
              className="flex gap-3 rounded-2xl border border-ink-100 bg-white p-4 print:break-inside-avoid"
            >
              <span
                className={cn(
                  'h-fit shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold',
                  rec.priority === 'high' && 'bg-clay-100 text-clay-800',
                  rec.priority === 'medium' && 'bg-wheat-100 text-wheat-700',
                  rec.priority === 'low' && 'bg-ink-100 text-ink-700',
                )}
              >
                {t(`growth.priority.${rec.priority}`)}
              </span>
              <div className="min-w-0">
                <p className="text-ink-900">
                  {t(`growth.rec.${rec.key}` as TranslationKey, { count: rec.count ?? 0 })}
                </p>
                <p className="mt-1 text-xs font-semibold text-ink-500">
                  {t(`growth.lever.${rec.lever}`)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-4 lg:grid-cols-2 print:grid-cols-2">
        <ShopTable
          title={t('growth.topHeading')}
          shops={data.top_shops}
          empty={t('growth.emptyTop')}
        />
        <ShopTable
          title={t('growth.quietHeading')}
          shops={data.quiet_shops}
          empty={t('growth.emptyQuiet')}
          more={data.health.unseen - data.quiet_shops.length}
        />
      </div>
    </>
  )
}

const W = 320
const H = 120
const TOP = 16

/**
 * One bar per week, with its number above it. Inline SVG like the other
 * admin charts, so it prints into the PDF as it looks on screen. Weeks run
 * left to right whatever the page direction.
 */
function WeeklyBars({
  label,
  values,
  weeks,
  barClass,
}: {
  label: string
  values: number[]
  weeks: string[]
  barClass: string
}) {
  const { locale } = useI18n()
  const max = Math.max(1, ...values)
  const slot = W / Math.max(1, values.length)
  const barWidth = slot * 0.62
  const dayLabel = (iso: string | undefined) =>
    iso
      ? new Date(`${iso}T00:00:00Z`).toLocaleDateString(locale === 'ar' ? 'ar-LB' : 'en-GB', {
          day: 'numeric',
          month: 'short',
          timeZone: 'UTC',
        })
      : ''

  return (
    <Card className="print:break-inside-avoid">
      <CardBody className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-semibold text-ink-700">{label}</p>
          <p className="text-2xl font-bold ltr-nums text-ink-900">{values[values.length - 1] ?? 0}</p>
        </div>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="mt-2 h-auto w-full"
          role="img"
          aria-label={`${label}: ${values.join(', ')}`}
        >
          <line x1={0} x2={W} y1={H - 0.5} y2={H - 0.5} stroke="#e6e5e0" />
          {values.map((value, index) => {
            const height = value === 0 ? 1.5 : Math.max(((H - TOP) * value) / max, 3)
            const x = index * slot + (slot - barWidth) / 2
            return (
              <g key={index}>
                <rect
                  x={x}
                  y={H - height}
                  width={barWidth}
                  height={height}
                  rx={3}
                  className={cn(barClass, index < values.length - 1 && 'opacity-60')}
                />
                <text
                  x={x + barWidth / 2}
                  y={H - height - 4}
                  textAnchor="middle"
                  fontSize={11}
                  className="fill-ink-500"
                >
                  {value}
                </text>
              </g>
            )
          })}
        </svg>
        <div dir="ltr" className="mt-1 flex justify-between text-xs text-ink-500">
          <span>{dayLabel(weeks[0])}</span>
          <span>{dayLabel(weeks[weeks.length - 1])}</span>
        </div>
      </CardBody>
    </Card>
  )
}

function HealthBar({ health, total }: { health: GrowthReport['health']; total: number }) {
  const { t } = useI18n()
  const parts = [
    { key: 'orders', value: health.with_orders, labelKey: 'growth.healthOrders', className: 'bg-brand-700' },
    { key: 'viewed', value: health.viewed_no_orders, labelKey: 'growth.healthViewed', className: 'bg-wheat-300' },
    { key: 'unseen', value: health.unseen, labelKey: 'growth.healthUnseen', className: 'bg-clay-400' },
  ] as const

  return (
    <section className="space-y-3 print:break-inside-avoid">
      <h2 className="text-xl">{t('growth.healthHeading')}</h2>
      <div className="flex h-6 overflow-hidden rounded-full bg-ink-100">
        {total > 0
          ? parts.map((part) =>
              part.value > 0 ? (
                <div
                  key={part.key}
                  className={part.className}
                  style={{ width: `${(part.value / total) * 100}%` }}
                />
              ) : null,
            )
          : null}
      </div>
      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {parts.map((part) => (
          <li key={part.key} className="flex items-center gap-2">
            <span className={cn('h-3 w-3 rounded-full', part.className)} aria-hidden="true" />
            <span className="text-ink-700">{t(part.labelKey)}</span>
            <span className="font-bold ltr-nums text-ink-900">{part.value}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ShopTable({
  title,
  shops,
  empty,
  more = 0,
}: {
  title: string
  shops: GrowthShopLine[]
  empty: string
  more?: number
}) {
  const { t } = useI18n()
  return (
    <Card className="print:break-inside-avoid">
      <CardBody className="p-4">
        <h2 className="text-lg">{title}</h2>
        {shops.length === 0 ? (
          <p className="mt-3 text-sm text-ink-500">{empty}</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-ink-500">
                <th className="py-2 text-start font-semibold">{t('growth.colShop')}</th>
                <th className="py-2 text-end font-semibold">{t('growth.colOrders')}</th>
                <th className="py-2 text-end font-semibold">{t('growth.colViews')}</th>
              </tr>
            </thead>
            <tbody>
              {shops.map((shop) => (
                <tr key={shop.slug} className="border-b border-ink-50 last:border-0">
                  <td className="py-2">
                    <Link
                      to={`/business/${encodeURIComponent(shop.slug)}`}
                      className="font-semibold text-brand-800 hover:underline"
                    >
                      {shop.name}
                    </Link>
                  </td>
                  <td className="py-2 text-end ltr-nums">{shop.orders}</td>
                  <td className="py-2 text-end ltr-nums">{shop.views}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {more > 0 ? (
          <p className="mt-2 text-xs text-ink-500">{t('growth.quietMore', { count: more })}</p>
        ) : null}
      </CardBody>
    </Card>
  )
}
