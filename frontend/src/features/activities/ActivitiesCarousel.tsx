import { useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { useI18n } from '@/i18n'
import { activityApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/format'

/**
 * The development activities' announcements, one photograph at a time (the
 * owners' ticket, 29 Oct 2026). A scroll-snap strip rather than a carousel
 * library: a finger swipes it on a phone with nothing to load, and the
 * arrows and dots only scroll the same strip. It never turns by itself --
 * a slide that moves while someone is reading it is one they lose.
 *
 * Nothing at all until an administrator keeps an activity with its
 * photograph, which is why the section can be on the page from the start.
 */
export function ActivitiesCarousel() {
  const { t, dir, locale } = useI18n()
  const rtl = dir === 'rtl'
  const activities = useQuery({ queryKey: queryKeys.activities, queryFn: activityApi.list })
  const items = activities.data ?? []
  const track = useRef<HTMLDivElement>(null)
  const [current, setCurrent] = useState(0)

  const onScroll = useCallback(() => {
    const el = track.current
    if (!el || el.clientWidth === 0) return
    // Negative in a right-to-left strip in every current browser.
    setCurrent(Math.round(Math.abs(el.scrollLeft) / el.clientWidth))
  }, [])

  useEffect(() => {
    setCurrent(0)
  }, [items.length])

  if (items.length === 0) return null

  const goTo = (index: number) => {
    const el = track.current
    if (!el) return
    const next = (index + items.length) % items.length
    el.scrollTo({ left: (rtl ? -1 : 1) * next * el.clientWidth, behavior: 'smooth' })
  }
  const arrow =
    'absolute top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-ink-900 shadow-card transition hover:bg-white sm:flex'

  return (
    <section className="bg-sand-50 py-10 sm:py-12" aria-labelledby="activities-carousel-title">
      <div className="container-page">
        <div className="mb-5 flex items-baseline justify-between gap-4">
          <h2
            id="activities-carousel-title"
            className="font-display text-2xl font-bold text-ink-900 sm:text-3xl"
          >
            {t('activities.carouselTitle')}
          </h2>
          <Link
            to="/activities"
            className="shrink-0 text-sm font-semibold text-brand-700 hover:underline"
          >
            {t('activities.viewAll')}
          </Link>
        </div>

        <div className="relative" aria-roledescription="carousel">
          <div
            ref={track}
            onScroll={onScroll}
            className="flex snap-x snap-mandatory overflow-x-auto overscroll-x-contain rounded-2xl [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {items.map((activity, index) => (
              <Link
                key={activity.id}
                to={`/activities/${encodeURIComponent(activity.slug)}`}
                className="relative block w-full shrink-0 snap-start"
                aria-roledescription="slide"
                aria-label={t('activities.slideLabel', {
                  index: index + 1,
                  count: items.length,
                  title: activity.title,
                })}
              >
                {activity.image_url ? (
                  <img
                    src={activity.image_url}
                    alt=""
                    loading={index === 0 ? 'eager' : 'lazy'}
                    decoding="async"
                    className="aspect-[4/3] w-full object-cover sm:aspect-[16/7]"
                  />
                ) : null}
                <div
                  className="absolute inset-0 bg-gradient-to-t from-ink-900/85 via-ink-900/25 to-transparent"
                  aria-hidden="true"
                />
                <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
                  {activity.starts_at ? (
                    <p className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-ink-900">
                      <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
                      {formatDate(activity.starts_at, locale)}
                    </p>
                  ) : null}
                  <h3
                    className="line-clamp-2 font-display text-xl font-bold text-white sm:text-3xl"
                    dir="auto"
                  >
                    {activity.title}
                  </h3>
                  {activity.summary ? (
                    <p className="mt-1 line-clamp-2 text-sm text-white/90 sm:text-base" dir="auto">
                      {activity.summary}
                    </p>
                  ) : null}
                </div>
              </Link>
            ))}
          </div>

          {items.length > 1 ? (
            <>
              <button
                type="button"
                onClick={() => goTo(current - 1)}
                aria-label={t('gallery.previous')}
                className={cn(arrow, 'start-3')}
              >
                {rtl ? (
                  <ChevronRight className="h-6 w-6" aria-hidden="true" />
                ) : (
                  <ChevronLeft className="h-6 w-6" aria-hidden="true" />
                )}
              </button>
              <button
                type="button"
                onClick={() => goTo(current + 1)}
                aria-label={t('gallery.next')}
                className={cn(arrow, 'end-3')}
              >
                {rtl ? (
                  <ChevronLeft className="h-6 w-6" aria-hidden="true" />
                ) : (
                  <ChevronRight className="h-6 w-6" aria-hidden="true" />
                )}
              </button>
            </>
          ) : null}
        </div>

        {items.length > 1 ? (
          <div className="mt-4 flex justify-center gap-2">
            {items.map((activity, index) => (
              <button
                key={activity.id}
                type="button"
                onClick={() => goTo(index)}
                aria-label={t('activities.slideLabel', {
                  index: index + 1,
                  count: items.length,
                  title: activity.title,
                })}
                aria-current={index === current ? 'true' : undefined}
                className={cn(
                  'h-2.5 rounded-full transition-all',
                  index === current ? 'w-6 bg-brand-700' : 'w-2.5 bg-ink-300 hover:bg-ink-500',
                )}
              />
            ))}
          </div>
        ) : null}
      </div>
    </section>
  )
}
