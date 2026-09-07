import { useQuery } from '@tanstack/react-query'
import {
  BadgeCheck,
  Check,
  Facebook,
  Globe,
  Instagram,
  Link2,
  MapPin,
  MessageCircle,
  Music2,
  Phone,
  Share2,
  Store,
  Youtube,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { publicBusinessApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT } from '@/i18n'
import type { SocialPlatform } from '@/types/api'
import { formatDate, formatPrice, PLATFORM_KEYS, telHref, whatsappHref } from '@/utils/format'

const PLATFORM_ICONS: Record<SocialPlatform, typeof Instagram> = {
  INSTAGRAM: Instagram,
  FACEBOOK: Facebook,
  TIKTOK: Music2,
  YOUTUBE: Youtube,
  WHATSAPP: MessageCircle,
  WEBSITE: Globe,
}

export function BusinessProfilePage() {
  const { slug = '' } = useParams()
  const [copied, setCopied] = useState(false)
  const t = useT()
  const { locale } = useI18n()

  const business = useQuery({
    queryKey: queryKeys.business(slug),
    queryFn: () => publicBusinessApi.bySlug(slug),
    enabled: slug.length > 0,
  })

  const data = business.data
  useSeo({
    title: data
      ? data.location
        ? `${data.name} — ${data.location.name_ar} | ${t('app.name')}`
        : `${data.name} | ${t('app.name')}`
      : t('app.name'),
    description: data?.short_description ?? undefined,
    image: data?.cover_url ?? data?.logo_url ?? null,
    canonicalPath: `/business/${encodeURIComponent(slug)}`,
  })

  const handleShare = async () => {
    const url = window.location.href
    const shareData = {
      title: data?.name ?? t('app.name'),
      text: data?.short_description ?? '',
      url,
    }
    // Native share on phones; clipboard elsewhere.
    if (navigator.share) {
      try {
        await navigator.share(shareData)
        return
      } catch {
        /* user dismissed the sheet — fall through to copying */
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2500)
    } catch {
      /* clipboard unavailable; nothing further we can do */
    }
  }

  if (business.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-52 w-full rounded-2xl sm:h-64" />
        <Skeleton className="mt-6 h-8 w-1/2" />
        <Skeleton className="mt-3 h-4 w-1/3" />
        <Skeleton className="mt-8 h-40 w-full" />
      </div>
    )
  }

  if (business.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={business.error} onRetry={() => void business.refetch()} />
        <div className="mt-6 text-center">
          <Button asChild variant="outline">
            <Link to="/businesses">{t('business.backToDirectory')}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const whatsapp = whatsappHref(
    data.whatsapp,
    t('business.whatsappMessage', { name: data.name }),
  )
  const phone = telHref(data.phone)
  const mapsUrl =
    data.maps_url ??
    (data.latitude !== null && data.longitude !== null
      ? `https://www.google.com/maps/search/?api=1&query=${data.latitude},${data.longitude}`
      : null)

  return (
    <article className="pb-16">
      <div className="relative h-52 bg-sand-200 sm:h-72">
        {data.cover_url ? (
          <img
            src={data.cover_url}
            alt={t('business.coverAlt', { name: data.name })}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sand-500">
            <Store className="h-16 w-16" aria-hidden="true" />
          </div>
        )}
      </div>

      <div className="container-page">
        {/* The cover image above is `relative` for its own layout, which makes
            it a positioned element — without z-index here too, it would paint
            over this non-positioned card (and the logo inside it) wherever
            the negative margin makes them overlap, regardless of DOM order. */}
        <div className="relative z-10 -mt-14 flex flex-col gap-4 rounded-2xl border border-ink-100 bg-white p-6 shadow-card sm:flex-row sm:items-end">
          <div className="h-24 w-24 shrink-0 overflow-hidden rounded-2xl border-4 border-white bg-sand-100 shadow-card">
            {data.logo_url ? (
              <img
                src={data.logo_url}
                alt={t('business.logoAlt', { name: data.name })}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <Store className="h-9 w-9" aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl sm:text-3xl">{data.name}</h1>
              <Badge className="bg-olive-100 text-olive-700">
                <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                {t('business.verified')}
              </Badge>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-500">
              {data.category ? (
                <Link to={`/businesses?category=${encodeURIComponent(data.category.slug)}`} className="font-semibold text-clay-600 hover:underline">
                  {data.custom_category_text || data.category.name_ar}
                </Link>
              ) : null}
              {data.location ? (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-4 w-4" aria-hidden="true" />
                  {data.location.name_ar}
                </span>
              ) : null}
            </div>
          </div>

          <Button variant="outline" onClick={() => void handleShare()} className="shrink-0">
            {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Share2 className="h-4 w-4" aria-hidden="true" />}
            {copied ? t('business.linkCopied') : t('business.share')}
          </Button>
        </div>

        {/* Contact CTAs sit directly under the header: on a phone this is the
            single most important action on the page. */}
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {whatsapp ? (
            <Button asChild variant="whatsapp" size="lg" block>
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-5 w-5" aria-hidden="true" />
                {t('business.whatsappCta')}
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button asChild size="lg" block>
              <a href={phone}>
                <Phone className="h-5 w-5" aria-hidden="true" />
                {t('business.callCta')}
              </a>
            </Button>
          ) : null}
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          <div className="space-y-8 lg:col-span-2">
            {data.description || data.short_description ? (
              <section aria-labelledby="about-heading">
                <h2 id="about-heading" className="mb-3 text-xl">
                  {t('business.aboutHeading')}
                </h2>
                <Card>
                  <CardBody>
                    <p className="whitespace-pre-line leading-loose text-ink-700">
                      {data.description || data.short_description}
                    </p>
                  </CardBody>
                </Card>
              </section>
            ) : null}


            {data.institution_name || data.founding_date || data.production_nature ? (
              <section aria-labelledby="producer-heading">
                <h2 id="producer-heading" className="mb-3 text-xl">
                  {t('business.producerHeading')}
                </h2>
                <Card>
                  <CardBody>
                    <dl className="grid gap-4 sm:grid-cols-2">
                      {data.institution_name ? (
                        <div>
                          <dt className="text-sm font-semibold text-ink-500">
                            {t('business.institutionLabel')}
                          </dt>
                          <dd className="mt-1 text-ink-700">{data.institution_name}</dd>
                        </div>
                      ) : null}
                      {data.founding_date ? (
                        <div>
                          <dt className="text-sm font-semibold text-ink-500">
                            {t('business.foundingDateLabel')}
                          </dt>
                          <dd className="mt-1 text-ink-700">
                            {formatDate(data.founding_date, locale)}
                          </dd>
                        </div>
                      ) : null}
                      {data.production_nature ? (
                        <div className="sm:col-span-2">
                          <dt className="text-sm font-semibold text-ink-500">
                            {t('business.productionLabel')}
                          </dt>
                          <dd className="mt-1 whitespace-pre-line leading-relaxed text-ink-700">
                            {data.production_nature}
                          </dd>
                        </div>
                      ) : null}
                    </dl>
                  </CardBody>
                </Card>
              </section>
            ) : null}

            {data.items.length > 0 ? (
              <section aria-labelledby="items-heading">
                <h2 id="items-heading" className="mb-3 text-xl">
                  {t('business.itemsHeading')}
                </h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  {data.items.map((item) => (
                    <Card key={item.id} className={item.is_available ? '' : 'opacity-60'}>
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.title} loading="lazy" className="h-40 w-full rounded-t-2xl object-cover" />
                      ) : null}
                      <CardBody className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <h3 className="font-bold text-ink-900">{item.title}</h3>
                          {formatPrice(item.price, item.currency) ? (
                            <span className="ltr-nums shrink-0 rounded-lg bg-sand-100 px-2.5 py-1 text-sm font-bold text-clay-700">
                              {formatPrice(item.price, item.currency)}
                            </span>
                          ) : null}
                        </div>
                        {item.description ? (
                          <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{item.description}</p>
                        ) : null}
                        {!item.is_available ? (
                          <Badge className="mt-3 bg-ink-100 text-ink-700">
                            {t('business.itemUnavailable')}
                          </Badge>
                        ) : null}
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </section>
            ) : null}

            {data.images.length > 0 ? (
              <section aria-labelledby="gallery-heading">
                <h2 id="gallery-heading" className="mb-3 text-xl">
                  {t('business.galleryHeading')}
                </h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {data.images.map((image) => (
                    <a
                      key={image.id}
                      href={image.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group overflow-hidden rounded-xl border border-ink-100 bg-sand-100"
                    >
                      <img
                        src={image.url}
                        alt={image.caption ?? t('business.galleryImageAlt', { name: data.name })}
                        loading="lazy"
                        className="h-32 w-full object-cover transition-transform duration-300 group-hover:scale-105 sm:h-40"
                      />
                    </a>
                  ))}
                </div>
              </section>
            ) : null}
          </div>

          <aside className="space-y-4">
            <Card>
              <CardBody className="space-y-4">
                <h2 className="text-lg font-bold">{t('business.contactHeading')}</h2>

                {data.phone ? (
                  <a href={telHref(data.phone) ?? '#'} className="flex items-center gap-3 text-ink-700 hover:text-clay-600">
                    <Phone className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    <span className="ltr-nums">{data.phone}</span>
                  </a>
                ) : null}

                {data.whatsapp && whatsapp ? (
                  <a href={whatsapp} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-ink-700 hover:text-clay-600">
                    <MessageCircle className="h-5 w-5 shrink-0 text-[#25D366]" aria-hidden="true" />
                    <span className="ltr-nums">{data.whatsapp}</span>
                  </a>
                ) : null}

                {data.website ? (
                  <a href={data.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 break-all text-ink-700 hover:text-clay-600">
                    <Globe className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    <span className="ltr-nums">{data.website}</span>
                  </a>
                ) : null}

                {data.address_text ? (
                  <p className="flex items-start gap-3 text-ink-700">
                    <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    {data.address_text}
                  </p>
                ) : null}

                {mapsUrl ? (
                  <Button asChild variant="outline" block>
                    <a href={mapsUrl} target="_blank" rel="noopener noreferrer">
                      <MapPin className="h-4 w-4" aria-hidden="true" />
                      {t('business.locationCta')}
                    </a>
                  </Button>
                ) : null}
              </CardBody>
            </Card>

            {data.social_links.length > 0 ? (
              <Card>
                <CardBody className="space-y-3">
                  <h2 className="text-lg font-bold">{t('business.followHeading')}</h2>
                  {data.social_links.map((link) => {
                    const Icon = PLATFORM_ICONS[link.platform] ?? Link2
                    return (
                      <a
                        key={link.platform}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 rounded-lg p-2 text-ink-700 transition-colors hover:bg-sand-100 hover:text-clay-600"
                      >
                        <Icon className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                        {t(PLATFORM_KEYS[link.platform])}
                      </a>
                    )
                  })}
                </CardBody>
              </Card>
            ) : null}
          </aside>
        </div>
      </div>
    </article>
  )
}
