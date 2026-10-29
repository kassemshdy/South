import { CalendarDays, GraduationCap, MapPin, MonitorPlay } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useI18n } from '@/i18n'
import type { Workshop } from '@/types/api'
import { formatDateTime, formatPrice } from '@/utils/format'

/** Where a workshop is: online, or its venue and town. */
export function workshopPlace(
  workshop: Workshop,
  t: (key: 'workshops.online' | 'common.listSeparator') => string,
): string {
  if (workshop.mode === 'ONLINE') return t('workshops.online')
  return [workshop.venue, workshop.location?.name_ar].filter(Boolean).join(t('common.listSeparator'))
}

/** A workshop in a list: when, where, by whom, and what it costs. */
export function WorkshopCard({ workshop }: { workshop: Workshop }) {
  const { t, locale } = useI18n()
  const price = formatPrice(workshop.price, workshop.currency)
  const place = workshopPlace(workshop, t)
  return (
    <Link
      to={`/workshops/${encodeURIComponent(workshop.slug)}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-ink-100 transition hover:shadow-lift"
    >
      {workshop.cover_url ? (
        <img src={workshop.cover_url} alt="" loading="lazy" className="aspect-[16/9] w-full object-cover" />
      ) : (
        <span className="flex aspect-[16/9] w-full items-center justify-center bg-brand-50 text-brand-700">
          <GraduationCap className="h-10 w-10" aria-hidden="true" />
        </span>
      )}
      <span className="flex flex-1 flex-col gap-2 p-4">
        <span className="flex items-start justify-between gap-2">
          <span className="font-bold text-ink-900 group-hover:text-brand-700" dir="auto">
            {workshop.title}
          </span>
          <span className="ltr-nums shrink-0 rounded-full bg-wheat-100 px-2.5 py-0.5 text-xs font-bold text-wheat-700">
            {price ?? t('workshops.free')}
          </span>
        </span>
        <span className="flex items-center gap-2 text-sm text-ink-700">
          <CalendarDays className="h-4 w-4 shrink-0 text-clay-600" aria-hidden="true" />
          {formatDateTime(workshop.starts_at, locale)}
        </span>
        {place ? (
          <span className="flex items-center gap-2 text-sm text-ink-700">
            {workshop.mode === 'ONLINE' ? (
              <MonitorPlay className="h-4 w-4 shrink-0 text-clay-600" aria-hidden="true" />
            ) : (
              <MapPin className="h-4 w-4 shrink-0 text-clay-600" aria-hidden="true" />
            )}
            {place}
          </span>
        ) : null}
        {workshop.trainer_name ? (
          <span className="text-sm text-ink-500" dir="auto">
            {t('workshops.trainer', { name: workshop.trainer_name })}
          </span>
        ) : null}
      </span>
    </Link>
  )
}
