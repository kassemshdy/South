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
import type { SocialPlatform } from '@/types/api'
import { formatPrice, PLATFORM_LABELS, telHref, whatsappHref } from '@/utils/format'

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

  const business = useQuery({
    queryKey: queryKeys.business(slug),
    queryFn: () => publicBusinessApi.bySlug(slug),
    enabled: slug.length > 0,
  })

  const data = business.data
  useSeo({
    title: data ? `${data.name}${data.location ? ` في ${data.location.name_ar}` : ''} | دليل الجنوب` : 'دليل الجنوب',
    description: data?.short_description ?? undefined,
    image: data?.cover_url ?? data?.logo_url ?? null,
    canonicalPath: `/business/${encodeURIComponent(slug)}`,
  })

  const handleShare = async () => {
    const url = window.location.href
    const shareData = { title: data?.name ?? 'دليل الجنوب', text: data?.short_description ?? '', url }
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
            <Link to="/businesses">العودة إلى دليل الأعمال</Link>
          </Button>
        </div>
      </div>
    )
  }

  const whatsapp = whatsappHref(data.whatsapp, `مرحباً، وجدت ${data.name} على دليل الجنوب.`)
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
          <img src={data.cover_url} alt={`صورة غلاف ${data.name}`} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-sand-500">
            <Store className="h-16 w-16" aria-hidden="true" />
          </div>
        )}
      </div>

      <div className="container-page">
        <div className="-mt-14 flex flex-col gap-4 rounded-2xl border border-ink-100 bg-white p-6 shadow-card sm:flex-row sm:items-end">
          <div className="h-24 w-24 shrink-0 overflow-hidden rounded-2xl border-4 border-white bg-sand-100 shadow-card">
            {data.logo_url ? (
              <img src={data.logo_url} alt={`شعار ${data.name}`} className="h-full w-full object-cover" />
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
                نشاط موثّق
              </Badge>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-500">
              {data.category ? (
                <Link to={`/businesses?category=${encodeURIComponent(data.category.slug)}`} className="font-semibold text-clay-600 hover:underline">
                  {data.category.name_ar}
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
            {copied ? 'تم نسخ الرابط' : 'مشاركة'}
          </Button>
        </div>

        {/* Contact CTAs sit directly under the header: on a phone this is the
            single most important action on the page. */}
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {whatsapp ? (
            <Button asChild variant="whatsapp" size="lg" block>
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-5 w-5" aria-hidden="true" />
                تواصل عبر واتساب
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button asChild size="lg" block>
              <a href={phone}>
                <Phone className="h-5 w-5" aria-hidden="true" />
                اتصل الآن
              </a>
            </Button>
          ) : null}
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          <div className="space-y-8 lg:col-span-2">
            {data.description || data.short_description ? (
              <section aria-labelledby="about-heading">
                <h2 id="about-heading" className="mb-3 text-xl">
                  نبذة عن النشاط
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

            {data.items.length > 0 ? (
              <section aria-labelledby="items-heading">
                <h2 id="items-heading" className="mb-3 text-xl">
                  المنتجات والخدمات
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
                          <Badge className="mt-3 bg-ink-100 text-ink-700">غير متوفر حالياً</Badge>
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
                  معرض الصور
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
                        alt={image.caption ?? `صورة من ${data.name}`}
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
                <h2 className="text-lg font-bold">معلومات التواصل</h2>

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
                      الموقع
                    </a>
                  </Button>
                ) : null}
              </CardBody>
            </Card>

            {data.social_links.length > 0 ? (
              <Card>
                <CardBody className="space-y-3">
                  <h2 className="text-lg font-bold">تابعنا</h2>
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
                        {PLATFORM_LABELS[link.platform]}
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
