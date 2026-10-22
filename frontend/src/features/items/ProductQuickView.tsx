import { useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { hasProductFacts, ProductFacts } from '@/features/items/ProductFacts'
import { useT } from '@/i18n'
import type { BusinessItem } from '@/types/api'
import { formatPrice } from '@/utils/format'

interface ProductQuickViewProps {
  item: BusinessItem
  open: boolean
  onOpenChange: (open: boolean) => void
  /** The shop page's own add-to-cart, so ordering works the same here. */
  action?: ReactNode
}

/**
 * A product opened from a shop page: its photo large, the gallery behind
 * it, and everything the owner wrote about it. A visitor used to see a
 * thumbnail and two lines and had nowhere to tap for more.
 *
 * The details come from `ProductFacts`, the same block the product's own
 * page shows, so the two never describe a product differently.
 */
export function ProductQuickView({ item, open, onOpenChange, action }: ProductQuickViewProps) {
  const t = useT()
  const photos = [
    ...(item.image_url ? [{ id: 'main', url: item.image_url, caption: null }] : []),
    ...item.images,
  ]
  const [shown, setShown] = useState(0)
  const current = photos[Math.min(shown, photos.length - 1)]
  const price = formatPrice(item.price, item.currency)

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setShown(0)
        onOpenChange(next)
      }}
    >
      <DialogContent title={item.title} className="max-w-2xl">
        {current ? (
          <img
            src={current.url}
            alt={current.caption ?? item.title}
            className="max-h-[60dvh] w-full rounded-xl bg-sand-100 object-contain"
          />
        ) : null}

        {photos.length > 1 ? (
          <ul className="mt-3 flex gap-2 overflow-x-auto">
            {photos.map((photo, index) => (
              <li key={photo.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => setShown(index)}
                  aria-label={photo.caption ?? item.title}
                  aria-current={index === shown ? 'true' : undefined}
                  className={`block h-16 w-16 overflow-hidden rounded-lg border-2 ${
                    index === shown ? 'border-brand-600' : 'border-transparent'
                  }`}
                >
                  <img src={photo.url} alt="" className="h-full w-full object-cover" />
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {price ? (
            <span className="ltr-nums rounded-lg bg-sand-100 px-2.5 py-1 font-bold text-brand-800">
              {price}
            </span>
          ) : null}
          {item.is_available ? null : (
            <Badge className="bg-ink-100 text-ink-700">{t('business.itemUnavailable')}</Badge>
          )}
        </div>

        {item.description ? (
          <p className="mt-3 whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
            {item.description}
          </p>
        ) : null}

        {hasProductFacts(item) ? (
          <div className="mt-5 border-t border-ink-100 pt-4">
            <h3 className="mb-3 font-bold text-ink-900">{t('products.detailHeading')}</h3>
            <ProductFacts item={item} />
          </div>
        ) : null}

        {action ? <div className="mt-5">{action}</div> : null}
      </DialogContent>
    </Dialog>
  )
}
