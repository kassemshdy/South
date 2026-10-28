import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { useI18n } from '@/i18n'
import type { StoryGroup } from '@/types/api'
import { cn } from '@/utils/cn'

/** How long one photo stays before the next, as on the apps people know. */
const PHOTO_MS = 5000

export function storyPage(group: StoryGroup): string {
  return `/${group.kind === 'business' ? 'business' : 'talent'}/${encodeURIComponent(group.slug)}`
}

/**
 * The stories row opened full screen: one listing's photos at a time, a bar
 * per photo along the top, each advancing on its own after a few seconds,
 * then on to the next listing. A tap on the start half goes back and on the
 * end half goes forward, a swipe goes to the next or previous listing, and
 * the arrow keys work too -- all following the page's direction, so in
 * Arabic "next" is to the left. Holding a finger down pauses.
 */
export function StoryViewer({
  groups,
  group,
  onGroupChange,
}: {
  groups: StoryGroup[]
  /** The listing shown; null when closed. */
  group: number | null
  onGroupChange: (group: number | null) => void
}) {
  const { t, locale } = useI18n()
  const rtl = locale === 'ar'
  const [photo, setPhoto] = useState(0)
  const [paused, setPaused] = useState(false)
  const touch = useRef<{ x: number; y: number } | null>(null)
  const open = group !== null && groups[group] !== undefined
  const current = open ? groups[group] : undefined
  const stories = current?.stories ?? []
  const story = stories[photo]

  // A new listing starts at its first photo.
  useEffect(() => setPhoto(0), [group])

  const forward = () => {
    if (group === null) return
    if (photo < stories.length - 1) setPhoto(photo + 1)
    else if (group < groups.length - 1) onGroupChange(group + 1)
    else onGroupChange(null)
  }
  const back = () => {
    if (group === null) return
    if (photo > 0) setPhoto(photo - 1)
    else if (group > 0) onGroupChange(group - 1)
  }

  useEffect(() => {
    if (!open || paused) return
    const timer = window.setTimeout(forward, PHOTO_MS)
    return () => window.clearTimeout(timer)
  })

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') (rtl ? forward : back)()
      if (event.key === 'ArrowRight') (rtl ? back : forward)()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(next) => (next ? null : onGroupChange(null))}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/95" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed inset-0 z-50 flex items-center justify-center focus:outline-none sm:p-6"
        >
          {current && story ? (
            <div className="relative flex h-full w-full max-w-[min(28rem,100%)] flex-col overflow-hidden bg-ink-900 sm:rounded-2xl">
              <DialogPrimitive.Title className="sr-only">{current.name}</DialogPrimitive.Title>

              <img
                key={story.id}
                src={story.image_url}
                alt={story.caption ?? current.name}
                className="absolute inset-0 h-full w-full object-contain"
              />

              {/* The two halves of the photo: back and forward. */}
              <div
                className="absolute inset-0 flex"
                onPointerDown={() => setPaused(true)}
                onPointerUp={() => setPaused(false)}
                onPointerLeave={() => setPaused(false)}
                onTouchStart={(event) => {
                  const point = event.touches[0]
                  touch.current = point ? { x: point.clientX, y: point.clientY } : null
                }}
                onTouchEnd={(event) => {
                  const start = touch.current
                  const end = event.changedTouches[0]
                  touch.current = null
                  if (!start || !end) return
                  const dx = end.clientX - start.x
                  if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(end.clientY - start.y)) return
                  event.preventDefault()
                  const swipedLeft = dx < 0
                  // A swipe skips the rest of this listing's photos.
                  const next = swipedLeft === rtl ? -1 : 1
                  if (group === null) return
                  const target = group + next
                  if (target >= 0 && target < groups.length) onGroupChange(target)
                  else if (target >= groups.length) onGroupChange(null)
                }}
              >
                <button
                  type="button"
                  aria-label={t('stories.previous')}
                  onClick={back}
                  className="h-full flex-1 focus-visible:outline-none"
                />
                <button
                  type="button"
                  aria-label={t('stories.next')}
                  onClick={forward}
                  className="h-full flex-1 focus-visible:outline-none"
                />
              </div>

              <div className="pointer-events-none relative space-y-3 bg-gradient-to-b from-black/70 to-transparent p-3 pb-8">
                <div className="flex gap-1" dir={rtl ? 'rtl' : 'ltr'}>
                  {stories.map((entry, index) => (
                    <span key={entry.id} className="h-1 flex-1 overflow-hidden rounded-full bg-white/30">
                      <span
                        key={`${entry.id}-${index === photo ? 'on' : 'off'}`}
                        className={cn(
                          'block h-full bg-white',
                          index < photo ? 'w-full' : 'w-0',
                          index === photo && 'animate-story-progress',
                        )}
                        style={
                          index === photo
                            ? {
                                animationDuration: `${PHOTO_MS}ms`,
                                animationPlayState: paused ? 'paused' : 'running',
                              }
                            : undefined
                        }
                      />
                    </span>
                  ))}
                </div>
                <div className="pointer-events-auto flex items-center justify-between gap-3">
                  <Link
                    to={storyPage(current)}
                    onClick={() => onGroupChange(null)}
                    className="flex min-w-0 items-center gap-2 text-white"
                  >
                    <span className="h-9 w-9 shrink-0 overflow-hidden rounded-full border-2 border-white bg-brand-700">
                      {current.image_url ? (
                        <img src={current.image_url} alt="" className="h-full w-full object-cover" />
                      ) : null}
                    </span>
                    <span dir="auto" className="truncate text-sm font-bold">
                      {current.name}
                    </span>
                  </Link>
                  <DialogPrimitive.Close
                    className="rounded-full p-2 text-white hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                    aria-label={t('common.close')}
                  >
                    <X className="h-6 w-6" aria-hidden="true" />
                  </DialogPrimitive.Close>
                </div>
              </div>

              <div className="pointer-events-none relative mt-auto space-y-3 bg-gradient-to-t from-black/80 to-transparent p-4 pt-10">
                {story.caption ? (
                  <p dir="auto" className="text-base font-semibold text-white">
                    {story.caption}
                  </p>
                ) : null}
                <Link
                  to={storyPage(current)}
                  onClick={() => onGroupChange(null)}
                  className="pointer-events-auto inline-flex rounded-xl bg-white px-4 py-2 text-sm font-bold text-ink-900 hover:bg-sand-100"
                >
                  {t(current.kind === 'business' ? 'stories.visitShop' : 'stories.visitProfile')}
                </Link>
              </div>
            </div>
          ) : null}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
