import { ExternalLink } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { ShareButton } from '@/components/ui/ShareButton'
import { SocialShare } from '@/components/ui/SocialShare'
import { ProductGallery } from '@/features/items/ProductGallery'
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
  /** Named in the share text, as on the product's own page. */
  businessName: string
}

/**
 * A product opened from a shop page: its photo large, the gallery behind
 * it, and everything the owner wrote about it. A visitor used to see a
 * thumbnail and two lines and had nowhere to tap for more.
 *
 * The details come from `ProductFacts`, the same block the product's own
 * page shows, so the two never describe a product differently.
 */
export function ProductQuickView({
  item,
  open,
  onOpenChange,
  action,
  businessName,
}: ProductQuickViewProps) {
  const t = useT()
  const price = formatPrice(item.price, item.currency)
  // Shared and linked by the product's own page, not the shop's: whoever
  // receives it lands on this product, with its gallery and order button.
  const path = `/product/${encodeURIComponent(item.slug)}`
  const shareUrl = typeof window === 'undefined' ? path : `${window.location.origin}${path}`
  const shareText = price
    ? t('products.shareText', { name: item.title, price, business: businessName })
    : t('products.shareTextNoPrice', { name: item.title, business: businessName })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={item.title} className="max-w-2xl">
        <ProductGallery title={item.title} imageUrl={item.image_url} images={item.images} />

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

        {/* An unavailable product has no public page to open or share. */}
        {item.is_available ? (
          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-ink-100 pt-4">
            <Button asChild variant="outline" size="sm">
              <Link to={path}>
                <ExternalLink className="size-4" aria-hidden />
                {t('products.openPage')}
              </Link>
            </Button>
            <ShareButton title={item.title} text={shareText} url={shareUrl} />
            <SocialShare text={shareText} url={shareUrl} />
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
