import * as DialogPrimitive from '@radix-ui/react-dialog'
import { ChevronLeft, ChevronRight, ExternalLink, Instagram, X, Youtube } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { useI18n } from '@/i18n'
import type { Reel } from '@/types/api'

/** Only these players are ever framed, whatever the API returned. */
const EMBED_ORIGINS: Record<Reel['provider'], string> = {
  youtube: 'https://www.youtube-nocookie.com/embed/',
  instagram: 'https://www.instagram.com/',
}

/** The site a reel plays from, drawn where a reel has no cover. */
export function ProviderIcon({ provider, className }: { provider: Reel['provider']; className?: string }) {
  const Icon = provider === 'youtube' ? Youtube : Instagram
  return <Icon className={className} aria-hidden="true" />
}

export function reelCaption(reel: Reel, locale: string): string | null {
  return locale === 'ar' ? reel.caption_ar ?? reel.caption_en : reel.caption_en ?? reel.caption_ar
}

/**
 * The home page's reels opened full screen, one at a time: a dark backdrop,
 * the reel in the middle in its site's own player (YouTube or Instagram),
 * and the next one a tap,
 * a swipe or an arrow key away -- the way news sites present their video
 * strips.
 *
 * YouTube or Instagram is contacted only here, once a visitor opens a reel:
 * the row on the page draws our own covers, so the page itself makes no
 * request to either. Directions follow the page's, as in the photo lightbox: in
 * Arabic the next reel is to the left. A swipe is read on the backdrop
 * around the player; touches on the player itself belong to the player.
 */
export function ReelPlayer({
  reels,
  index,
  onIndexChange,
}: {
  reels: Reel[]
  /** The reel shown; null when closed. */
  index: number | null
  onIndexChange: (index: number | null) => void
}) {
  const { t, locale } = useI18n()
  const rtl = locale === 'ar'
  const touchStart = useRef<number | null>(null)
  const count = reels.length
  const open = index !== null && count > 0
  const current = open ? reels[index] : undefined
  const caption = current ? reelCaption(current, locale) : null

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

  const arrow =
    'absolute top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/15 text-white backdrop-blur transition-colors hover:bg-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white'

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(next) => (next ? null : onIndexChange(null))}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/95" />
        <DialogPrimitive.Content
          className="fixed inset-0 z-50 flex flex-col items-center justify-center px-3 py-14 focus:outline-none"
          aria-describedby={undefined}
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
          <DialogPrimitive.Title className="sr-only">
            {caption ?? t('home.reelsTitle')}
          </DialogPrimitive.Title>
          <DialogPrimitive.Close
            className="absolute end-3 top-3 rounded-full bg-white/15 p-2.5 text-white transition-colors hover:bg-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            aria-label={t('common.close')}
          >
            <X className="h-6 w-6" aria-hidden="true" />
          </DialogPrimitive.Close>

          {current ? (
            <>
              <div className="relative flex w-full max-w-[min(26rem,100%)] flex-1 items-center justify-center">
                {current.embed_url.startsWith(EMBED_ORIGINS[current.provider]) ? (
                  <iframe
                    // A new frame per reel, so the last one stops playing.
                    key={current.id}
                    src={current.embed_url}
                    title={caption ?? t('home.reelsTitle')}
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                    allowFullScreen
                    className="h-full max-h-[48rem] w-full rounded-xl bg-white"
                  />
                ) : null}
              </div>
              <div className="mt-3 flex w-full max-w-[26rem] items-center justify-between gap-3 text-sm text-white/80">
                <span dir="auto" className="line-clamp-2">
                  {caption}
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  {count > 1 ? (
                    <span className="ltr-nums">
                      {t('gallery.counter', { current: (index ?? 0) + 1, total: count })}
                    </span>
                  ) : null}
                  <a
                    href={current.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-white hover:underline"
                  >
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    {t(current.provider === 'youtube' ? 'reels.openOnYoutube' : 'reels.openOnInstagram')}
                  </a>
                </span>
              </div>
              {count > 1 ? (
                <>
                  <button
                    type="button"
                    onClick={() => go(-1)}
                    aria-label={t('reels.previous')}
                    className={`${arrow} start-2 sm:start-6`}
                  >
                    {rtl ? (
                      <ChevronRight className="h-7 w-7" aria-hidden="true" />
                    ) : (
                      <ChevronLeft className="h-7 w-7" aria-hidden="true" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => go(1)}
                    aria-label={t('reels.next')}
                    className={`${arrow} end-2 sm:end-6`}
                  >
                    {rtl ? (
                      <ChevronLeft className="h-7 w-7" aria-hidden="true" />
                    ) : (
                      <ChevronRight className="h-7 w-7" aria-hidden="true" />
                    )}
                  </button>
                </>
              ) : null}
            </>
          ) : null}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
