import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useI18n, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { GrowthTotals } from '@/types/api'

/**
 * How the platform grew: running totals per day for the last 30 days, one
 * small chart per measure. Small multiples rather than one chart, because
 * products run into the hundreds while talent is in the tens, and a shared
 * axis would flatten every line but one. Every row counts, whatever its
 * status -- applications waiting for review are growth too.
 */
const SERIES: { key: keyof GrowthTotals; labelKey: TranslationKey; color: string }[] = [
  { key: 'businesses', labelKey: 'admin.navBusinesses', color: '#2a78d6' },
  { key: 'talents', labelKey: 'admin.navTalent', color: '#eb6834' },
  { key: 'products', labelKey: 'admin.statItems', color: '#1baf7a' },
  { key: 'orders', labelKey: 'admin.navOrders', color: '#eda100' },
]

export function GrowthPanel() {
  const { t } = useI18n()
  const growth = useQuery({ queryKey: queryKeys.adminGrowth, queryFn: () => adminApi.growth(30) })

  return (
    <section>
      <h2 className="text-xl">{t('admin.growthHeading')}</h2>
      <p className="mb-4 mt-1 text-sm text-ink-500">{t('admin.growthSubtitle')}</p>
      {growth.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {SERIES.map((series) => (
            <Skeleton key={series.key} className="h-44 rounded-2xl" />
          ))}
        </div>
      ) : growth.isError ? (
        <ErrorState error={growth.error} onRetry={() => void growth.refetch()} />
      ) : growth.data ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {SERIES.map((series) => (
            <GrowthChart
              key={series.key}
              label={t(series.labelKey)}
              color={series.color}
              days={growth.data.days}
              values={growth.data.totals[series.key]}
            />
          ))}
        </div>
      ) : null}
    </section>
  )
}

const W = 320
const H = 120
const PAD = { top: 10, right: 8, bottom: 6, left: 8 }

function GrowthChart({
  label,
  color,
  days,
  values,
}: {
  label: string
  color: string
  days: string[]
  values: number[]
}) {
  const { t, locale } = useI18n()
  const [hover, setHover] = useState<number | null>(null)
  const last = values[values.length - 1] ?? 0
  const today = last - (values[values.length - 2] ?? last)
  const max = Math.max(1, ...values)
  const x = (index: number) => PAD.left + ((W - PAD.left - PAD.right) * index) / Math.max(1, values.length - 1)
  const y = (value: number) => PAD.top + (H - PAD.top - PAD.bottom) * (1 - value / max)
  const points = values.map((value, index) => `${x(index)},${y(value)}`).join(' ')
  const shownIndex = hover ?? values.length - 1
  const dayLabel = (iso: string | undefined) =>
    iso
      ? new Date(`${iso}T00:00:00Z`).toLocaleDateString(locale === 'ar' ? 'ar-LB' : 'en-GB', {
          day: 'numeric',
          month: 'short',
          timeZone: 'UTC',
        })
      : ''

  return (
    <Card>
      <CardBody className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-semibold text-ink-700">{label}</p>
          <p className="text-sm text-ink-500">
            <span className="ltr-nums text-2xl font-bold text-ink-900">{values[shownIndex]}</span>
            {hover === null && today > 0 ? (
              <span className="ms-2 ltr-nums">{t('admin.growthToday', { count: today })}</span>
            ) : (
              <span className="ms-2">{dayLabel(days[shownIndex])}</span>
            )}
          </p>
        </div>
        {/* Time runs left to right whatever the page direction: SVG
            coordinates do not mirror in RTL. */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="mt-2 h-auto w-full"
          role="img"
          aria-label={`${label}: ${values[0]} → ${last}`}
          onMouseLeave={() => setHover(null)}
        >
          <line x1={PAD.left} x2={W - PAD.right} y1={y(0)} y2={y(0)} stroke="#e6e5e0" />
          <polyline points={points} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
          {hover !== null ? (
            <>
              <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={y(0)} stroke="#c3c2b7" strokeDasharray="3 3" />
              <circle cx={x(hover)} cy={y(values[hover] ?? 0)} r={4} fill={color} stroke="#fff" strokeWidth={2} />
            </>
          ) : (
            <circle cx={x(values.length - 1)} cy={y(last)} r={4} fill={color} stroke="#fff" strokeWidth={2} />
          )}
          {/* A full-height strip per day: a hit target wider than the line. */}
          {values.map((_, index) => (
            <rect
              key={index}
              x={x(index) - (W - PAD.left - PAD.right) / (2 * Math.max(1, values.length - 1))}
              y={0}
              width={(W - PAD.left - PAD.right) / Math.max(1, values.length - 1)}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHover(index)}
            />
          ))}
        </svg>
        {/* Dates as text, not SVG: Arabic in an SVG <text> is laid out
            right-to-left and was clipped at the edges. */}
        <div dir="ltr" className="mt-1 flex justify-between text-xs text-ink-500">
          <span>{dayLabel(days[0])}</span>
          <span>{dayLabel(days[days.length - 1])}</span>
        </div>
      </CardBody>
    </Card>
  )
}
