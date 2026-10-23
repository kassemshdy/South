import { Quote } from 'lucide-react'

import { useI18n } from '@/i18n'
import { formatDate } from '@/utils/format'
import type { Testimonial } from '@/types/api'
import { Stars } from '@/features/testimonials/Stars'

/**
 * The praise published on a listing -- a business or a service profile.
 *
 * Published by an administrator's approval alone (the owners' decision,
 * round 3); the listing's owner neither approves nor hides. The authors are
 * not verified, which is what the line under the heading says, so it renders
 * with the heading rather than as a footnote.
 *
 * **The stars count every published rating and nothing else**, so the
 * average is the average of what this list shows and a visitor can check it.
 */
export function TestimonialList({
  testimonials,
  average,
  count,
}: {
  testimonials: Testimonial[]
  average: number | null
  count: number
}) {
  const { t, locale } = useI18n()

  return (
    <section aria-labelledby="testimonials-heading">
      <h2 id="testimonials-heading" className="mb-1 text-xl">
        {t('testimonials.heading')}
      </h2>
      {average !== null && count > 0 ? (
        <p className="mb-1 flex items-center gap-2 text-sm font-semibold text-ink-700">
          <Stars value={average} />
          <span className="ltr-nums">
            {t('testimonials.ratingSummary', {
              average: average.toFixed(1),
              count: String(count),
            })}
          </span>
        </p>
      ) : null}
      <p className="mb-3 text-xs text-ink-400">{t('testimonials.disclaimer')}</p>

      {testimonials.length === 0 ? (
        <p className="rounded-xl bg-sand-50 p-4 text-sm text-ink-500">
          {t('testimonials.empty')}
        </p>
      ) : (
        <ul className="space-y-3">
          {testimonials.map((entry) => (
            <li
              key={entry.id}
              className="rounded-xl border border-ink-100 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <Quote className="h-4 w-4 text-clay-300" aria-hidden="true" />
                {entry.rating ? <Stars value={entry.rating} /> : null}
              </div>
              <p className="mt-1.5 leading-relaxed text-ink-700">{entry.body}</p>
              <p className="mt-2 text-sm font-semibold text-ink-500">
                {entry.author_name}
                <span className="ms-2 font-normal text-ink-300">
                  {formatDate(entry.created_at, locale)}
                </span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
