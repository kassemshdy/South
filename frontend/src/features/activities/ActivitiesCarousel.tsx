import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useI18n } from '@/i18n'
import { activityApi } from '@/services/api/endpoints'
import type { CarouselSlide } from '@/types/api'
import { cn } from '@/utils/cn'

/** Under the `activities` prefix, so anything that refreshes the activities refreshes it too. */
export const CAROUSEL_QUERY_KEY = ['activities', 'carousel'] as const

const AUTOPLAY_MS = 6000

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

/**
 * The announcements carousel (the owners' ticket, 31 Oct 2026): one
 * component, on the home page and at the top of /activities, reading the
 * slides in the order an administrator set them.
 *
 * A scroll-snap strip, so a finger swipes it on a phone with nothing to
 * load; the arrows, the dots and autoplay only scroll the same strip.
 * Autoplay turns every six seconds and stops while the pointer is over it,
 * a finger is on it, or it has keyboard focus -- and not at all for anyone
 * who asked their system for less motion. Nothing renders without slides.
 *
 * `heading` puts a title row above it (the home page); /activities shows it
 * bare, under the page's own title.
 */
export function ActivitiesCarousel({ heading = true }: { heading?: boolean }) {
  const { t, dir } = useI18n()
  const rtl = dir === 'rtl'
  const slides = useQuery({ queryKey: CAROUSEL_QUERY_KEY, queryFn: activityApi.carousel })
  const items = slides.data ?? []
  const track = useRef<HTMLDivElement>(null)
  const [current, setCurrent] = useState(0)
  const [paused, setPaused] = useState(false)

  const onScroll = useCallback(() => {
    const el = track.current
    if (!el || el.clientWidth === 0) return
    // Negative in a right-to-left strip in every current browser.
    setCurrent(Math.round(Math.abs(el.scrollLeft) / el.clientWidth))
  }, [])

  const goTo = useCallback(
    (index: number) => {
      const el = track.current
      if (!el || items.length === 0) return
      const next = (index + items.length) % items.length
      el.scrollTo({ left: (rtl ? -1 : 1) * next * el.clientWidth, behavior: 'smooth' })
    },
    [items.length, rtl],
  )

  useEffect(() => {
    setCurrent(0)
  }, [items.length])

  useEffect(() => {
    if (paused || items.length < 2 || prefersReducedMotion()) return
    const timer = window.setInterval(() => goTo(current + 1), AUTOPLAY_MS)
    return () => window.clearInterval(timer)
  }, [paused, items.length, current, goTo])

  if (items.length === 0) return null

  const arrow =
    'absolute top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-ink-900 shadow-card transition hover:bg-white sm:flex'

  const strip = (
    <div
      className="relative"
      role="region"
      aria-roledescription="carousel"
      aria-label={t('activitiesPage.carouselLabel')}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onTouchStart={() => setPaused(true)}
      onTouchEnd={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div
        ref={track}
        onScroll={onScroll}
        className="flex snap-x snap-mandatory overflow-x-auto overscroll-x-contain rounded-2xl [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {items.map((slide, index) => (
          <SlideLink
            key={slide.id}
            slide={slide}
            label={t('activities.slideLabel', {
              index: index + 1,
              count: items.length,
              title: slide.title ?? '',
            })}
          >
            {/* The whole picture, never cropped (the owners' ticket, 5 Nov
                2026): a square or tall poster sits in the middle of the
                16:9 frame over a blurred copy of itself. A 16:9 card image
                fills the frame exactly. */}
            <div className="relative aspect-[16/9] w-full overflow-hidden bg-ink-900">
              <img
                src={slide.image_url}
                alt=""
                aria-hidden="true"
                loading={index === 0 ? 'eager' : 'lazy'}
                decoding="async"
                className="absolute inset-0 h-full w-full scale-110 object-cover opacity-60 blur-2xl"
              />
              <img
                src={slide.image_url}
                alt=""
                loading={index === 0 ? 'eager' : 'lazy'}
                decoding="async"
                className="relative h-full w-full object-contain"
              />
            </div>
            {slide.title ? (
              <>
                <div
                  className="absolute inset-0 bg-gradient-to-t from-ink-900/85 via-ink-900/20 to-transparent"
                  aria-hidden="true"
                />
                <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
                  <h3
                    className="line-clamp-2 font-display text-xl font-bold text-white sm:text-3xl"
                    dir="auto"
                  >
                    {slide.title}
                  </h3>
                </div>
              </>
            ) : null}
          </SlideLink>
        ))}
      </div>

      {items.length > 1 ? (
        <>
          {/* Previous sits at the start (the right in Arabic) and points
              back the way the reader came; next at the end. */}
          <button
            type="button"
            onClick={() => goTo(current - 1)}
            aria-label={t('activitiesPage.prevSlide')}
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
            aria-label={t('activitiesPage.nextSlide')}
            className={cn(arrow, 'end-3')}
          >
            {rtl ? (
              <ChevronLeft className="h-6 w-6" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
          <div className="absolute inset-x-0 bottom-3 z-10 flex justify-center gap-2">
            {items.map((slide, index) => (
              <button
                key={slide.id}
                type="button"
                onClick={() => goTo(index)}
                aria-label={t('activities.slideLabel', {
                  index: index + 1,
                  count: items.length,
                  title: slide.title ?? '',
                })}
                aria-current={index === current ? 'true' : undefined}
                className={cn(
                  'h-2.5 rounded-full shadow transition-all',
                  index === current ? 'w-6 bg-white' : 'w-2.5 bg-white/60 hover:bg-white/90',
                )}
              />
            ))}
          </div>
        </>
      ) : null}
    </div>
  )

  if (!heading) return strip

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
        {strip}
      </div>
    </section>
  )
}

/** The whole slide is the link: inside the site, out of it in a new tab, or nothing. */
function SlideLink({
  slide,
  label,
  children,
}: {
  slide: CarouselSlide
  label: string
  children: ReactNode
}) {
  const className = 'relative block w-full shrink-0 snap-start'
  if (!slide.href) {
    return (
      <div className={className} aria-roledescription="slide" aria-label={label}>
        {children}
      </div>
    )
  }
  if (slide.external) {
    return (
      <a
        href={slide.href}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
        aria-roledescription="slide"
        aria-label={label}
      >
        {children}
      </a>
    )
  }
  return (
    <Link to={slide.href} className={className} aria-roledescription="slide" aria-label={label}>
      {children}
    </Link>
  )
}
