import { Eye } from 'lucide-react'

import { useT } from '@/i18n'
import type { ListingViews } from '@/types/api'

/**
 * What an owner gets back for being in the directory.
 *
 * Until this existed, a listing was approved and then nothing happened: the
 * person the whole project is meant to expose could not see the exposure,
 * so there was no reason to come back, keep the listing current, or tell the
 * shop next door. One number and a shape fix that.
 *
 * **It says views, never visitors.** Nothing identifying anyone is stored,
 * so the number cannot be a count of people — and an owner who works out
 * that one number here oversells will stop believing the rest. The explainer
 * says so in as many words rather than leaving it to be inferred.
 */
export function ViewsPanel({
  views,
  windowDays,
}: {
  views: ListingViews | undefined
  windowDays: number
}) {
  const t = useT()
  const recent = views?.views_recent ?? 0
  const total = views?.views_window ?? 0

  return (
    <div className="mt-4 rounded-xl border border-sand-200 bg-sand-50/70 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-400">
            <Eye className="h-3.5 w-3.5" aria-hidden="true" />
            {t('insights.viewsHeading')}
          </p>
          {recent > 0 ? (
            <p className="mt-1 text-sm font-bold text-clay-900">
              {t('insights.viewsThisWeek', { count: recent })}
            </p>
          ) : (
            <p className="mt-1 text-sm font-semibold text-ink-500">{t('insights.noViewsYet')}</p>
          )}
          <p className="mt-0.5 text-xs text-ink-400">
            {total > 0
              ? t('insights.viewsWindow', { count: total, days: windowDays })
              : t('insights.noViewsHint')}
          </p>
        </div>

        {views && total > 0 ? (
          <Sparkline
            series={views.series}
            label={t('insights.sparklineLabel', { days: windowDays })}
          />
        ) : null}
      </div>

      <p className="mt-2.5 text-[11px] leading-relaxed text-ink-300">
        {t('insights.viewsExplainer')}
      </p>
    </div>
  )
}

/**
 * A bar per day, drawn as inline SVG rather than pulled from a chart
 * library — the audience is on mid-range phones on mobile data, and this is
 * a few hundred bytes against a few hundred kilobytes.
 *
 * The SVG carries the numbers as its accessible label; a picture of a trend
 * with no text is nothing at all to a screen reader.
 */
function Sparkline({ series, label }: { series: number[]; label: string }) {
  const peak = Math.max(...series, 1)
  const width = series.length * 5 - 1

  return (
    <svg
      viewBox={`0 0 ${width} 20`}
      className="h-10 w-24 shrink-0 text-clay-500"
      role="img"
      aria-label={`${label}: ${series.join(', ')}`}
      preserveAspectRatio="none"
    >
      {series.map((value, index) => {
        // A day with views is never invisible: a hairline still reads as
        // "something happened", where a zero-height bar reads as a gap.
        const height = value === 0 ? 0.75 : Math.max((value / peak) * 20, 2)
        return (
          <rect
            key={index}
            x={index * 5}
            y={20 - height}
            width={4}
            height={height}
            rx={1}
            fill="currentColor"
            opacity={value === 0 ? 0.25 : 1}
          />
        )
      })}
    </svg>
  )
}
