import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { inMemory } from '@/utils/shrinkImage'
import { cn } from '@/utils/cn'

/** A frame shape, written as the ratio people know it by. */
export type CropRatio = '1:1' | '4:3' | '16:9' | '3:1' | '9:16'

/**
 * The shapes each upload is offered, matched to where the photo is drawn:
 * a square logo badge, a wide cover banner, product and gallery photos in
 * the usual photo shapes, and a reel card standing tall. The first is the
 * one the window opens on.
 */
export const CROP_SHAPES = {
  logo: ['1:1'],
  cover: ['3:1'],
  product: ['4:3', '1:1', '16:9'],
  gallery: ['4:3', '1:1', '16:9'],
  reel: ['9:16'],
  story: ['9:16'],
} as const satisfies Record<string, readonly CropRatio[]>

export type CropShape = keyof typeof CROP_SHAPES

const RATIO: Record<CropRatio, number> = {
  '1:1': 1,
  '4:3': 4 / 3,
  '16:9': 16 / 9,
  '3:1': 3,
  '9:16': 9 / 16,
}

/** The longest side of a cropped photo; the server shrinks it further. */
const MAX_OUTPUT = 2000
const MAX_ZOOM = 4

interface View {
  /** The image point at the frame's centre, as fractions of its size. */
  fx: number
  fy: number
  zoom: number
}

const CENTRED: View = { fx: 0.5, fy: 0.5, zoom: 1 }

/**
 * Lets someone choose the part of a photo that is kept before it is uploaded:
 * drag to move it, the slider (or the wheel) to zoom. Every upload of a
 * photo that is drawn in a fixed shape goes through it, so what the owner
 * frames here is what visitors see rather than whatever the card happens to
 * cut off. «Use as it is» sends the photo untouched.
 *
 * The result is a JPEG on a white background: the server re-encodes every
 * photo as JPEG anyway, and white is what it puts behind a transparent logo.
 */
export function useCropStep(shape: CropShape): {
  crop: (file: File) => Promise<File | null>
  dialog: ReactNode
} {
  const [pending, setPending] = useState<{ file: File; resolve: (file: File | null) => void } | null>(
    null,
  )
  const toast = useToast()
  const t = useT()
  const crop = useCallback(
    async (picked: File): Promise<File | null> => {
      // Held in memory straight away: on Android a picked photo can become
      // unreadable later, after the owner has filled in the rest of the form.
      let file: File
      try {
        file = await inMemory(picked)
      } catch {
        toast.error(t('images.photoUnreadable'))
        return null
      }
      return new Promise<File | null>((resolve) => setPending({ file, resolve }))
    },
    [toast, t],
  )
  const finish = (file: File | null) => {
    pending?.resolve(file)
    setPending(null)
  }
  const dialog = (
    <ImageCropDialog
      key={pending ? `${pending.file.name}-${pending.file.lastModified}-${pending.file.size}` : 'closed'}
      file={pending?.file ?? null}
      ratios={CROP_SHAPES[shape]}
      onDone={finish}
    />
  )
  return { crop, dialog }
}

/** Several photos picked at once, offered to the crop window one by one. */
export async function cropEach(
  crop: (file: File) => Promise<File | null>,
  files: File[],
): Promise<File[]> {
  const kept: File[] = []
  for (const file of files) {
    const cropped = await crop(file)
    if (cropped) kept.push(cropped)
  }
  return kept
}

function ImageCropDialog({
  file,
  ratios,
  onDone,
}: {
  file: File | null
  ratios: readonly CropRatio[]
  /** The cropped photo, the original, or null when cancelled. */
  onDone: (file: File | null) => void
}) {
  const t = useT()
  const [ratio, setRatio] = useState<CropRatio>(ratios[0] ?? '1:1')
  const [view, setView] = useState<View>(CENTRED)
  const [source, setSource] = useState<string | null>(null)
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null)
  const [width, setWidth] = useState(0)
  const [busy, setBusy] = useState(false)
  const observer = useRef<ResizeObserver | null>(null)
  const image = useRef<HTMLImageElement>(null)
  const drag = useRef<{ id: number; x: number; y: number } | null>(null)

  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    setSource(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  // The frame's size follows the dialog's; measured once it is on screen.
  const measure = useCallback((node: HTMLDivElement | null) => {
    observer.current?.disconnect()
    observer.current = null
    if (!node) return
    observer.current = new ResizeObserver(() => setWidth(node.clientWidth))
    observer.current.observe(node)
    setWidth(node.clientWidth)
  }, [])

  const aspect = RATIO[ratio]
  // A tall frame is held to a little over half the screen's height.
  const maxHeight = typeof window === 'undefined' ? 480 : window.innerHeight * 0.55
  const frameW = Math.max(0, Math.min(width, maxHeight * aspect))
  const frameH = frameW / aspect

  const scaleFor = (zoom: number) =>
    natural ? Math.max(frameW / natural.w, frameH / natural.h) * zoom : 1

  /** Keeps the photo covering the whole frame. */
  const clamp = (next: View): View => {
    if (!natural || frameW === 0) return next
    const s = scaleFor(next.zoom)
    const halfX = frameW / (2 * natural.w * s)
    const halfY = frameH / (2 * natural.h * s)
    return {
      zoom: next.zoom,
      fx: Math.min(1 - halfX, Math.max(halfX, next.fx)),
      fy: Math.min(1 - halfY, Math.max(halfY, next.fy)),
    }
  }

  const scale = scaleFor(view.zoom)
  const shown = clamp(view)
  const left = natural ? frameW / 2 - shown.fx * natural.w * scale : 0
  const top = natural ? frameH / 2 - shown.fy * natural.h * scale : 0

  const zoomTo = (zoom: number) =>
    setView((current) => clamp({ ...current, zoom: Math.min(MAX_ZOOM, Math.max(1, zoom)) }))

  const apply = async () => {
    const img = image.current
    if (!file || !img || !natural || frameW === 0) return
    setBusy(true)
    try {
      const sw = frameW / scale
      const sh = frameH / scale
      const sx = -left / scale
      const sy = -top / scale
      const k = Math.min(1, MAX_OUTPUT / Math.max(sw, sh))
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(sw * k))
      canvas.height = Math.max(1, Math.round(sh * k))
      const context = canvas.getContext('2d')
      if (!context) {
        onDone(file)
        return
      }
      context.fillStyle = '#ffffff'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.92),
      )
      if (!blob) {
        onDone(file)
        return
      }
      const name = `${file.name.replace(/\.[^.]+$/, '') || 'photo'}.jpg`
      onDone(new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() }))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={file !== null} onOpenChange={(open) => (open ? null : onDone(null))}>
      <DialogContent title={t('crop.title')} description={t('crop.hint')} className="max-w-2xl">
        <div className="space-y-4">
          {ratios.length > 1 ? (
            <div className="flex flex-wrap gap-2" role="group" aria-label={t('crop.shape')}>
              {ratios.map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={ratio === option}
                  onClick={() => {
                    setRatio(option)
                    setView(CENTRED)
                  }}
                  className={cn(
                    'ltr-nums rounded-full px-4 py-1.5 text-sm font-semibold transition-colors',
                    ratio === option
                      ? 'bg-brand-700 text-white'
                      : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
                  )}
                >
                  {option}
                </button>
              ))}
            </div>
          ) : null}

          <div ref={measure} className="w-full">
            {/* Positions are physical, so the frame is laid out left to right
                whatever the page's direction. */}
            <div
              dir="ltr"
              className="relative mx-auto cursor-grab touch-none select-none overflow-hidden rounded-xl bg-ink-900 active:cursor-grabbing"
              style={{ width: frameW, height: frameH }}
              onPointerDown={(event) => {
                event.currentTarget.setPointerCapture(event.pointerId)
                drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY }
              }}
              onPointerMove={(event) => {
                const start = drag.current
                if (!start || start.id !== event.pointerId || !natural) return
                const dx = event.clientX - start.x
                const dy = event.clientY - start.y
                drag.current = { ...start, x: event.clientX, y: event.clientY }
                setView((current) => {
                  const from = clamp(current)
                  return clamp({
                    ...from,
                    fx: from.fx - dx / (natural.w * scale),
                    fy: from.fy - dy / (natural.h * scale),
                  })
                })
              }}
              onPointerUp={() => {
                drag.current = null
              }}
              onPointerCancel={() => {
                drag.current = null
              }}
              onWheel={(event) => zoomTo(view.zoom * (event.deltaY < 0 ? 1.08 : 1 / 1.08))}
            >
              {source ? (
                <img
                  ref={image}
                  src={source}
                  alt=""
                  draggable={false}
                  onLoad={(event) =>
                    setNatural({
                      w: event.currentTarget.naturalWidth,
                      h: event.currentTarget.naturalHeight,
                    })
                  }
                  className="pointer-events-none absolute max-w-none"
                  style={
                    natural
                      ? { left, top, width: natural.w * scale, height: natural.h * scale }
                      : { visibility: 'hidden' }
                  }
                />
              ) : null}
            </div>
          </div>

          <label className="flex items-center gap-3 text-sm font-semibold text-ink-700">
            <span className="shrink-0">{t('crop.zoom')}</span>
            <input
              type="range"
              min={1}
              max={MAX_ZOOM}
              step={0.01}
              value={view.zoom}
              onChange={(event) => zoomTo(Number(event.target.value))}
              className="w-full accent-brand-700"
            />
          </label>

          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => onDone(null)}>
              {t('common.cancel')}
            </Button>
            <Button type="button" variant="outline" onClick={() => file && onDone(file)}>
              {t('crop.useOriginal')}
            </Button>
            <Button type="button" loading={busy} disabled={!natural} onClick={() => void apply()}>
              {t('crop.apply')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
