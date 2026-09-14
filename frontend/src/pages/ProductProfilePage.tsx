import { useQuery } from '@tanstack/react-query'
import { MessageCircle, Package, Phone, Store } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { ShareButton } from '@/components/ui/ShareButton'
import { AddToCartButton } from '@/features/cart/AddToCartButton'
import { FavouriteButton } from '@/features/favourites/FavouriteButton'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT } from '@/i18n'
import { publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, formatPrice, telHref, whatsappHref } from '@/utils/format'

export function ProductProfilePage() {
  const { slug = '' } = useParams()
  const t = useT()
  const { locale } = useI18n()

  const product = useQuery({
    queryKey: queryKeys.product(slug),
    queryFn: () => publicItemApi.bySlug(slug),
    enabled: slug.length > 0,
  })

  const data = product.data
  useSeo({
    title: data ? `${data.title} — ${data.business.name} | ${t('app.name')}` : t('app.name'),
    description: data?.description ?? undefined,
    image: data?.image_url ?? null,
    canonicalPath: `/product/${encodeURIComponent(slug)}`,
  })

  if (product.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="mt-6 h-8 w-1/2" />
        <Skeleton className="mt-3 h-4 w-1/3" />
      </div>
    )
  }

  if (product.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={product.error} onRetry={() => void product.refetch()} />
        <div className="mt-6 text-center">
          <Button asChild variant="outline">
            <Link to="/products">{t('products.backToDirectory')}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const businessUrl = `/business/${encodeURIComponent(data.business.slug)}`
  const whatsapp = whatsappHref(
    data.business.whatsapp,
    t('business.whatsappMessage', { name: data.business.name }),
  )
  const phone = telHref(data.business.phone)
  const price = formatPrice(data.price, data.currency)
  const shareText = price
    ? t('products.shareText', { name: data.title, price, business: data.business.name })
    : t('products.shareTextNoPrice', { name: data.title, business: data.business.name })

  return (
    <article className="container-page py-10">
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="h-64 overflow-hidden rounded-2xl bg-sand-100 sm:h-80">
            {data.image_url ? (
              <img src={data.image_url} alt={data.title} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <Package className="h-16 w-16" aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-wrap items-start justify-between gap-3">
            {/* Owner-authored text carries its own direction — see BusinessCard. */}
            <h1 className="text-2xl sm:text-3xl" dir="auto">{data.title}</h1>
            {price ? (
              <Badge className="ltr-nums bg-sand-100 px-3 py-1.5 text-base font-bold text-clay-700">
                {price}
              </Badge>
            ) : null}
          </div>

          {/* A photo, a name and a price is the most passed-around thing this
              site has, and until now it was the one page with no way to pass
              it. The share text carries the price, because that is what makes
              a stranger open the link. */}
          <div className="mt-5 flex flex-wrap gap-2">
            {/* Only for something actually orderable: a product page reached
                while unavailable has nothing to add. */}
            <AddToCartButton
              target={{
                businessSlug: data.business.slug,
                businessName: data.business.name,
                whatsapp: data.business.whatsapp,
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
            <ShareButton title={data.title} text={shareText} />
            <FavouriteButton
              subject="PRODUCT"
              slug={data.slug}
              title={data.title}
              imageUrl={data.image_url}
            />
          </div>

          {data.description ? (
            <p className="mt-4 whitespace-pre-line leading-loose text-ink-700" dir="auto">
              {data.description}
            </p>
          ) : null}

          {data.images.length > 0 ? (
            <ul className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {data.images.map((image) => (
                <li key={image.id} className="overflow-hidden rounded-xl bg-sand-100">
                  <img src={image.url} alt={image.caption ?? data.title} className="h-24 w-full object-cover sm:h-28" />
                </li>
              ))}
            </ul>
          ) : null}

          {data.good_type ||
          data.brand_name ||
          data.ingredients ||
          data.manufactured_at ||
          data.expiry_date ||
          data.net_weight ||
          data.external_link ? (
            <section aria-labelledby="product-detail-heading" className="mt-6">
              <h2 id="product-detail-heading" className="mb-3 text-xl">
                {t('products.detailHeading')}
              </h2>
              <Card>
                <CardBody>
                  <dl className="grid gap-4 sm:grid-cols-2">
                    {data.good_type ? (
                      <div>
                        <dt className="text-sm font-semibold text-ink-500">{t('products.goodTypeLabel')}</dt>
                        <dd className="mt-1 text-ink-700">{data.good_type}</dd>
                      </div>
                    ) : null}
                    {data.brand_name ? (
                      <div>
                        <dt className="text-sm font-semibold text-ink-500">{t('products.brandNameLabel')}</dt>
                        <dd className="mt-1 text-ink-700">{data.brand_name}</dd>
                      </div>
                    ) : null}
                    {data.net_weight ? (
                      <div>
                        <dt className="text-sm font-semibold text-ink-500">{t('products.netWeightLabel')}</dt>
                        <dd className="mt-1 text-ink-700">{data.net_weight}</dd>
                      </div>
                    ) : null}
                    {data.manufactured_at ? (
                      <div>
                        <dt className="text-sm font-semibold text-ink-500">
                          {t('products.manufacturedAtLabel')}
                        </dt>
                        <dd className="mt-1 text-ink-700">{formatDate(data.manufactured_at, locale)}</dd>
                      </div>
                    ) : null}
                    {data.expiry_date ? (
                      <div>
                        <dt className="text-sm font-semibold text-ink-500">{t('products.expiryDateLabel')}</dt>
                        <dd className="mt-1 text-ink-700">{formatDate(data.expiry_date, locale)}</dd>
                      </div>
                    ) : null}
                    {data.ingredients ? (
                      <div className="sm:col-span-2">
                        <dt className="text-sm font-semibold text-ink-500">{t('products.ingredientsLabel')}</dt>
                        <dd className="mt-1 whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                          {data.ingredients}
                        </dd>
                      </div>
                    ) : null}
                    {data.external_link ? (
                      <div className="sm:col-span-2">
                        <dt className="text-sm font-semibold text-ink-500">{t('products.externalLinkLabel')}</dt>
                        <dd className="mt-1">
                          <a
                            href={data.external_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="break-all text-clay-600 underline"
                          >
                            {data.external_link}
                          </a>
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                </CardBody>
              </Card>
            </section>
          ) : null}
        </div>

        <aside className="space-y-4">
          <Card>
            <CardBody className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sand-100 text-clay-600">
                  <Store className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <Link to={businessUrl} className="block truncate font-bold text-ink-900 hover:text-clay-600">
                    {data.business.name}
                  </Link>
                  {data.business.location ? (
                    <p className="text-sm text-ink-500">{data.business.location.name_ar}</p>
                  ) : null}
                </div>
              </div>

              <Button asChild variant="outline" block>
                <Link to={businessUrl}>{t('products.viewBusinessCta')}</Link>
              </Button>

              {whatsapp ? (
                <Button asChild variant="whatsapp" block>
                  <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                    <MessageCircle className="h-5 w-5" aria-hidden="true" />
                    {t('business.whatsappCta')}
                  </a>
                </Button>
              ) : null}
              {phone ? (
                <Button asChild block>
                  <a href={phone}>
                    <Phone className="h-5 w-5" aria-hidden="true" />
                    {t('business.callCta')}
                  </a>
                </Button>
              ) : null}
            </CardBody>
          </Card>
        </aside>
      </div>
    </article>
  )
}
