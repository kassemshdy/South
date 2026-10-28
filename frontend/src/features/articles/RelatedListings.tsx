import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { BusinessCard } from '@/features/businesses/BusinessCard'
import { ProductCard } from '@/features/items/ProductCard'
import { useT } from '@/i18n'
import { publicBusinessApi, publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Article } from '@/types/api'

const SHOWN = 4

/**
 * The end of an article: products and shops in the category and place the
 * administrator said it is about, newest first, each row linking on to the
 * directory with the same filters. Nothing at all for an article that names
 * neither, and a row with no matches is left out.
 */
export function RelatedListings({ article }: { article: Article }) {
  const t = useT()
  const filters = {
    ...(article.category ? { category: article.category.slug } : {}),
    ...(article.location ? { location: article.location.slug } : {}),
  }
  const enabled = Object.keys(filters).length > 0
  const productQuery = { ...filters, sort: 'newest' as const, page_size: SHOWN }
  const shopQuery = { ...filters, page_size: SHOWN }

  const products = useQuery({
    queryKey: queryKeys.products(productQuery),
    queryFn: () => publicItemApi.search(productQuery),
    enabled,
  })
  const shops = useQuery({
    queryKey: queryKeys.businesses(shopQuery),
    queryFn: () => publicBusinessApi.search(shopQuery),
    enabled,
  })
  if (!enabled) return null

  const more = new URLSearchParams(filters).toString()
  const productList = products.data?.items ?? []
  const shopList = shops.data?.items ?? []

  return (
    <>
      {productList.length > 0 ? (
        <Row title={t('article.relatedProducts')} to={`/products?${more}`} more={t('home.viewAll')}>
          {productList.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </Row>
      ) : null}
      {shopList.length > 0 ? (
        <Row title={t('article.relatedShops')} to={`/businesses?${more}`} more={t('home.viewAll')}>
          {shopList.map((business) => (
            <BusinessCard key={business.id} business={business} />
          ))}
        </Row>
      ) : null}
    </>
  )
}

function Row({ title, to, more, children }: { title: string; to: string; more: string; children: ReactNode }) {
  return (
    <section className="mt-12 border-t border-ink-100 pt-8">
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-bold text-ink-900 sm:text-2xl">{title}</h2>
        <Link to={to} className="shrink-0 text-sm font-semibold text-brand-700 hover:underline">
          {more}
        </Link>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">{children}</div>
    </section>
  )
}
