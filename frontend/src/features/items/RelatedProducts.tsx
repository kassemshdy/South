import { useQuery } from '@tanstack/react-query'
import { Package, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { AddToCartButton } from '@/features/cart/AddToCartButton'
import { ProductQuickView } from '@/features/items/ProductQuickView'
import { useT } from '@/i18n'
import { publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { BusinessItem, ProductDetail, ProductSummary } from '@/types/api'
import { formatPrice } from '@/utils/format'

/** The quick view takes a shop's own item; a public product reads the same. */
function asItem(detail: ProductDetail): BusinessItem {
  return { ...detail, is_available: true, sort_order: 0 }
}

/**
 * One related product opened in place, the way a shop page opens one: the
 * details are fetched when the popup opens, so a row of eight costs one
 * request until someone is interested.
 */
function QuickViewer({ slug, onClose }: { slug: string; onClose: () => void }) {
  const detail = useQuery({
    queryKey: queryKeys.product(slug),
    queryFn: () => publicItemApi.bySlug(slug),
  })
  if (!detail.data) return null
  const data = detail.data
  return (
    <ProductQuickView
      item={asItem(data)}
      open
      onOpenChange={(open) => (open ? undefined : onClose())}
      businessName={data.business.name}
      action={
        <AddToCartButton
          target={{
            businessSlug: data.business.slug,
            businessName: data.business.name,
            whatsapp: data.business.whatsapp,
            phone: data.business.phone,
          }}
          line={{
            itemId: data.id,
            title: data.title,
            price: data.price,
            currency: data.currency,
            imageUrl: data.image_url,
            quantity: 1,
          }}
        />
      }
    />
  )
}

/**
 * "You may also like" under a product: the same shop's other products first,
 * then others in its category -- the second item in the order. Each opens in
 * a popup with its photos, details and order button, without leaving the
 * page. Nothing at all when there is nothing related.
 */
export function RelatedProducts({ slug }: { slug: string }) {
  const t = useT()
  const [open, setOpen] = useState<string | null>(null)
  const related = useQuery({
    queryKey: queryKeys.relatedProducts(slug),
    queryFn: () => publicItemApi.related(slug),
  })
  const items = related.data ?? []
  if (items.length === 0) return null
  return (
    <section aria-labelledby="related-heading" className="mt-12 border-t border-ink-100 pt-8">
      <h2 id="related-heading" className="mb-5 text-xl sm:text-2xl">
        {t('products.relatedTitle')}
      </h2>
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => setOpen(item.slug)}
              className="block w-full overflow-hidden rounded-2xl bg-white text-start shadow-card ring-1 ring-ink-100 transition hover:shadow-lift focus-visible:ring-2 focus-visible:ring-brand-600"
            >
              <Thumb item={item} className="aspect-square w-full" />
              <span className="block p-3">
                <span className="line-clamp-2 font-semibold text-ink-900" dir="auto">
                  {item.title}
                </span>
                <span className="mt-1 block truncate text-xs text-ink-500" dir="auto">
                  {item.business.name}
                </span>
                {formatPrice(item.price, item.currency) ? (
                  <span className="ltr-nums mt-1 block text-sm font-bold text-brand-800">
                    {formatPrice(item.price, item.currency)}
                  </span>
                ) : null}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {open ? <QuickViewer slug={open} onClose={() => setOpen(null)} /> : null}
    </section>
  )
}

function Thumb({ item, className }: { item: ProductSummary; className?: string }) {
  const src = item.image_thumb_url ?? item.image_url
  return src ? (
    <img src={src} alt="" loading="lazy" className={`${className ?? ''} object-cover`} />
  ) : (
    <span className={`${className ?? ''} flex items-center justify-center bg-sand-100 text-sand-500`}>
      <Package className="h-8 w-8" aria-hidden="true" />
    </span>
  )
}

/**
 * The product page's side column: what other visitors are opening most this
 * month, as a short list. The product being looked at is left out.
 */
export function TrendingProducts({ excludeId }: { excludeId: string }) {
  const t = useT()
  const trending = useQuery({
    queryKey: queryKeys.topViewedProducts,
    queryFn: publicItemApi.topViewed,
  })
  const items = (trending.data ?? []).filter((item) => item.id !== excludeId).slice(0, 5)
  if (items.length === 0) return null
  return (
    <Card>
      <CardBody className="p-4">
        <h2 className="mb-3 flex items-center gap-2 text-lg">
          <TrendingUp className="h-5 w-5 text-clay-600" aria-hidden="true" />
          {t('products.trendingTitle')}
        </h2>
        <ul className="divide-y divide-ink-100">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/product/${encodeURIComponent(item.slug)}`}
                className="flex items-center gap-3 py-2.5 hover:text-brand-700"
              >
                <Thumb item={item} className="h-14 w-14 shrink-0 rounded-xl" />
                <span className="min-w-0">
                  <span className="line-clamp-2 text-sm font-semibold text-ink-900" dir="auto">
                    {item.title}
                  </span>
                  {formatPrice(item.price, item.currency) ? (
                    <span className="ltr-nums text-xs font-bold text-brand-800">
                      {formatPrice(item.price, item.currency)}
                    </span>
                  ) : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}
