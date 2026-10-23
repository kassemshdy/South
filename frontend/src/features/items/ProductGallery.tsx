import { useState } from 'react'

import type { ItemImage } from '@/types/api'

/**
 * A product's photos: the main one large, and every photo as a thumbnail
 * that switches it. Used by the product page and the shop page's quick view,
 * so an owner's gallery is seen the same way in both.
 *
 * `object-contain` rather than `cover`: a product photo is evidence of what
 * is being sold, and cropping it to fit a box can cut off the part that
 * matters.
 */
export function ProductGallery({
  title,
  imageUrl,
  images,
  className = 'max-h-[60dvh]',
}: {
  title: string
  imageUrl: string | null
  images: ItemImage[]
  /** Height limit of the large photo. */
  className?: string
}) {
  const photos = [
    ...(imageUrl ? [{ id: 'main', url: imageUrl, caption: null }] : []),
    ...images.map((image) => ({ id: image.id, url: image.url, caption: image.caption })),
  ]
  const [shown, setShown] = useState(0)
  const current = photos[Math.min(shown, photos.length - 1)]
  if (!current) return null

  return (
    <div>
      <img
        src={current.url}
        alt={current.caption ?? title}
        className={`w-full rounded-xl bg-sand-100 object-contain ${className}`}
      />
      {photos.length > 1 ? (
        <ul className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {photos.map((photo, index) => (
            <li key={photo.id} className="shrink-0">
              <button
                type="button"
                onClick={() => setShown(index)}
                aria-label={photo.caption ?? title}
                aria-current={index === shown ? 'true' : undefined}
                className={`block h-16 w-16 overflow-hidden rounded-lg border-2 sm:h-20 sm:w-20 ${
                  index === shown ? 'border-brand-600' : 'border-transparent'
                }`}
              >
                <img src={photo.url} alt="" className="h-full w-full object-cover" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
