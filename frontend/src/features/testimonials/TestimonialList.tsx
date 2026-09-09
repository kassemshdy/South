import { Quote } from 'lucide-react'

import { useI18n } from '@/i18n'
import { formatDate } from '@/utils/format'
import type { Testimonial } from '@/types/api'

/**
 * The praise an owner chose to display.
 *
 * **The disclaimer is not decoration.** These are owner-approved, so an owner
 * can display flattering text and withhold anything else — which means they
 * are not independent evidence and the page must not let a reader think they
 * are. The issue that asked for this said so explicitly: *"this is not a
 * review system and should not be presented as one. Anyone reading it should
 * be able to tell."* Removing that line turns an honest feature into a
 * misleading one, so it renders with the heading rather than as a footnote.
 *
 * There is deliberately no count anywhere near a listing card: a count of
 * owner-selected praise would rank listings by how diligently their owners
 * collected compliments, and create pressure to farm them.
 */
export function TestimonialList({ testimonials }: { testimonials: Testimonial[] }) {
  const { t, locale } = useI18n()

  return (
    <section aria-labelledby="testimonials-heading">
      <h2 id="testimonials-heading" className="mb-1 text-xl">
        {t('testimonials.heading')}
      </h2>
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
              <Quote className="h-4 w-4 text-clay-300" aria-hidden="true" />
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
