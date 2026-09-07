import { MapPin, Package } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import type { ProductSummary } from '@/types/api'
import { formatPrice } from '@/utils/format'

export function ProductCard({ product }: { product: ProductSummary }) {
  const t = useT()
  const profileUrl = `/product/${encodeURIComponent(product.slug)}`
  const businessUrl = `/business/${encodeURIComponent(product.business.slug)}`
  const price = formatPrice(product.price, product.currency)

  return (
    <article className="group flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift">
      <Link to={profileUrl} className="block" tabIndex={-1} aria-hidden="true">
        <div className="relative h-36 overflow-hidden bg-sand-100">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sand-500">
              <Package className="h-10 w-10" aria-hidden="true" />
            </div>
          )}
        </div>
      </Link>

      {/* dir="auto" so an Arabic listing still reads right-to-left on an
          English page, and an English one reads left-to-right on an Arabic
          page: owner-authored content carries its own direction, independent
          of the UI language. */}
      <div className="flex flex-1 flex-col p-5" dir="auto">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {product.business.category ? (
            <Badge className="bg-sand-100 text-clay-700">{product.business.category.name_ar}</Badge>
          ) : null}
          {price ? (
            <span className="ltr-nums text-sm font-bold text-clay-700">{price}</span>
          ) : null}
        </div>

        <h3 className="text-lg font-bold text-ink-900">
          <Link to={profileUrl} className="transition-colors hover:text-clay-600">
            {product.title}
          </Link>
        </h3>

        <p className="mt-1.5 flex items-center gap-1 text-sm text-ink-500">
          <Link to={businessUrl} className="truncate hover:text-clay-600">
            {product.business.name}
          </Link>
          {product.business.location ? (
            <span className="inline-flex shrink-0 items-center gap-1">
              <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
              {product.business.location.name_ar}
            </span>
          ) : null}
        </p>

        <div className="mt-auto pt-4">
          <Button asChild size="sm" variant="outline" block>
            <Link to={businessUrl}>{t('products.visitBusiness')}</Link>
          </Button>
        </div>
      </div>
    </article>
  )
}
