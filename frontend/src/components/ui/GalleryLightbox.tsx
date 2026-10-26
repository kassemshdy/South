import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useI18n } from '@/i18n'

export interface LightboxImage {
  id: string
  url: string
  caption: string | null
}

/**
 * A gallery photo opened large, in place, with the rest one tap or swipe
 * away. The galleries used to link each photo to its file, which opened a
 * bare image in a new tab and took the visitor off the page.
 *
 * Arrows and swipes follow the page's direction: in Arabic the next photo
 * is to the left, as the next page of a book is.
 */
export function GalleryLightbox({
  title,
  images,
  index,
  onIndexChange,
}: {
  title: string
  images: LightboxImage[]
  /** The photo shown; null when closed. */
  index: number | null
  onIndexChange: (index: number | null) => void
}) {
  const { t, locale } = useI18n()
  const rtl = locale === 'ar'
  const touchStart = useRef<number | null>(null)
  const count = images.length
  const open = index !== null && count > 0
  const current = open ? images[index] : undefined

  const go = (step: 1 | -1) => {
    if (index === null || count < 2) return
    onIndexChange((index + step + count) % count)
  }

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') go(rtl ? 1 : -1)
      if (event.key === 'ArrowRight') go(rtl ? -1 : 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const button =
    'absolute top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-ink-900 shadow-lift transition-colors hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500'

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? null : onIndexChange(null))}>
      <DialogContent title={title} className="max-w-4xl">
        {current ? (
          <figure>
            <div
              className="relative"
              onTouchStart={(event) => {
                touchStart.current = event.touches[0]?.clientX ?? null
              }}
              onTouchEnd={(event) => {
                const start = touchStart.current
                const end = event.changedTouches[0]?.clientX
                touchStart.current = null
                if (start === null || end === undefined || Math.abs(end - start) < 50) return
                const swipedLeft = end < start
                go(swipedLeft === rtl ? -1 : 1)
              }}
            >
              <img
                src={current.url}
                alt={current.caption ?? title}
                className="mx-auto max-h-[70dvh] w-full rounded-xl bg-sand-100 object-contain"
              />
              {count > 1 ? (
                <>
                  <button
                    type="button"
                    onClick={() => go(-1)}
                    aria-label={t('gallery.previous')}
                    className={`${button} start-2`}
                  >
                    {rtl ? (
                      <ChevronRight className="h-6 w-6" aria-hidden="true" />
                    ) : (
                      <ChevronLeft className="h-6 w-6" aria-hidden="true" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => go(1)}
                    aria-label={t('gallery.next')}
                    className={`${button} end-2`}
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
            <figcaption className="mt-3 flex items-center justify-between gap-3 text-sm text-ink-500">
              <span dir="auto">{current.caption}</span>
              {count > 1 ? (
                <span className="shrink-0">
                  {t('gallery.counter', { current: (index ?? 0) + 1, total: count })}
                </span>
              ) : null}
            </figcaption>
          </figure>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
