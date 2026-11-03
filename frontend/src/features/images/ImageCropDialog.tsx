import { useEffect, useRef, useState, type PointerEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useT } from '@/i18n'

interface ImageCropDialogProps {
  /** The picked file; null keeps the dialog closed. */
  file: File | null
  /** Width over height of the place the image is shown (1 for a square card). */
  aspect: number
  /** Other shapes the person may pick instead, shown as ratio buttons. */
  ratios?: number[]
  onCancel: () => void
  onCropped: (file: File) => void
}

/** Longest side of the uploaded crop: plenty for a card or a cover, and small. */
const MAX_SIDE = 1600
const FRAME_WIDTH = 320

/**
 * Crop a picked photo to the exact shape the site shows it in (the owners'
 * request, 28 Oct 2026), before it is uploaded: drag to choose the part,
 * slide to zoom. What is inside the frame is what the card or cover shows,
 * so nobody discovers a cut-off product on the live page.
 *
 * The crop happens in the browser on a canvas; the file sent is a JPEG of
 * the framed part only, at most MAX_SIDE on its long side.
 */
/** "4:3" for 4/3, "1:1" for 1 -- numbers, so no copy is needed. */
function ratioLabel(ratio: number): string {
  for (const [w, h] of [[1, 1], [4, 3], [3, 4], [16, 9], [9, 16], [3, 1], [3, 2], [2, 3]] as const) {
    if (Math.abs(ratio - w / h) < 0.01) return `${w}:${h}`
  }
  return ratio.toFixed(2)
}

export function ImageCropDialog({ file, aspect: initial, ratios, onCancel, onCropped }: ImageCropDialogProps) {
  const t = useT()
  const [src, setSrc] = useState<string | null>(null)
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState<{ x: number; y: number } | null>(null)
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null)
  const image = useRef<HTMLImageElement>(null)
  const [aspect, setAspect] = useState(initial)

  const frameW = FRAME_WIDTH
  const frameH = Math.round(FRAME_WIDTH / aspect)

  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    setSrc(url)
    setNatural(null)
    setZoom(1)
    setOffset(null)
    setAspect(initial)
    return () => URL.revokeObjectURL(url)
  }, [file, initial])

  // The image always covers the frame: the smallest scale that does, times zoom.
  const scale = natural ? Math.max(frameW / natural.w, frameH / natural.h) * zoom : 1
  const shownW = natural ? natural.w * scale : frameW
  const shownH = natural ? natural.h * scale : frameH
  const clamp = (x: number, y: number) => ({
    x: Math.min(0, Math.max(frameW - shownW, x)),
    y: Math.min(0, Math.max(frameH - shownH, y)),
  })
  // Centred until the person moves it; always kept inside the frame.
  const position = offset
    ? clamp(offset.x, offset.y)
    : { x: (frameW - shownW) / 2, y: (frameH - shownH) / 2 }

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { x: event.clientX, y: event.clientY, ox: position.x, oy: position.y }
  }
  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return
    setOffset(
      clamp(
        drag.current.ox + event.clientX - drag.current.x,
        drag.current.oy + event.clientY - drag.current.y,
      ),
    )
  }
  const onPointerUp = () => {
    drag.current = null
  }

  const save = () => {
    if (!file || !natural || !image.current) return
    const sx = -position.x / scale
    const sy = -position.y / scale
    const sw = frameW / scale
    const sh = frameH / scale
    const ratio = Math.min(1, MAX_SIDE / Math.max(sw, sh))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(sw * ratio)
    canvas.height = Math.round(sh * ratio)
    const context = canvas.getContext('2d')
    if (!context) return
    context.drawImage(image.current, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (!blob) return
        const name = file.name.replace(/\.[^.]+$/, '') + '.jpg'
        onCropped(new File([blob], name, { type: 'image/jpeg' }))
      },
      'image/jpeg',
      0.9,
    )
  }

  return (
    <Dialog open={file !== null} onOpenChange={(next) => (next ? null : onCancel())}>
      <DialogContent title={t('crop.title')} description={t('crop.hint')} className="max-w-md">
        <div className="flex flex-col items-center gap-4">
          <div
            className="relative touch-none overflow-hidden rounded-xl bg-ink-900 ring-2 ring-brand-700"
            style={{ width: frameW, height: frameH }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            {src ? (
              <img
                ref={image}
                src={src}
                alt=""
                draggable={false}
                onLoad={(event) =>
                  setNatural({ w: event.currentTarget.naturalWidth, h: event.currentTarget.naturalHeight })
                }
                className="absolute max-w-none cursor-move select-none"
                style={{ width: shownW, height: shownH, left: position.x, top: position.y }}
              />
            ) : null}
          </div>
          {ratios && ratios.length > 1 ? (
            <div className="flex flex-wrap justify-center gap-2" role="group" aria-label={t('crop.ratio')}>
              {ratios.map((ratio) => (
                <button
                  key={ratio}
                  type="button"
                  aria-pressed={Math.abs(ratio - aspect) < 0.001}
                  onClick={() => {
                    setAspect(ratio)
                    setOffset(null)
                    setZoom(1)
                  }}
                  className={
                    Math.abs(ratio - aspect) < 0.001
                      ? 'ltr-nums rounded-full bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white'
                      : 'ltr-nums rounded-full bg-white px-3 py-1.5 text-sm font-semibold text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100'
                  }
                >
                  {ratioLabel(ratio)}
                </button>
              ))}
            </div>
          ) : null}
          <label className="flex w-full items-center gap-3 text-sm font-semibold">
            {t('crop.zoom')}
            <input
              type="range"
              min={1}
              max={4}
              step={0.01}
              value={zoom}
              onChange={(event) => {
                setOffset(position)
                setZoom(Number(event.target.value))
              }}
              className="flex-1 accent-brand-700"
            />
          </label>
          <div className="flex w-full justify-end gap-2">
            <Button variant="ghost" onClick={onCancel}>
              {t('common.cancel')}
            </Button>
            <Button onClick={save} disabled={!natural}>
              {t('crop.save')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
