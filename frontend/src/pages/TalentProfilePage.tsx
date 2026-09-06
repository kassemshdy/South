import { useQuery } from '@tanstack/react-query'
import {
  BadgeCheck,
  Check,
  Globe,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Share2,
  UserRound,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { telHref, whatsappHref } from '@/utils/format'

export function TalentProfilePage() {
  const { slug = '' } = useParams()
  const [copied, setCopied] = useState(false)
  const t = useT()

  const talent = useQuery({
    queryKey: queryKeys.talent(slug),
    queryFn: () => publicTalentApi.bySlug(slug),
    enabled: slug.length > 0,
  })

  const data = talent.data
  useSeo({
    title: data
      ? data.location
        ? `${data.display_name} — ${data.location.name_ar} | ${t('app.name')}`
        : `${data.display_name} | ${t('app.name')}`
      : t('app.name'),
    description: data?.headline ?? undefined,
    image: data?.photo_url ?? null,
    canonicalPath: `/talent/${encodeURIComponent(slug)}`,
  })

  const handleShare = async () => {
    const url = window.location.href
    const shareData = {
      title: data?.display_name ?? t('app.name'),
      text: data?.headline ?? '',
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
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable — the URL is in the address bar anyway */
    }
  }

  if (talent.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="mt-8 h-40 w-full" />
      </div>
    )
  }

  if (talent.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={talent.error} onRetry={() => void talent.refetch()} />
        <div className="mt-6 text-center">
          <Button asChild variant="outline">
            <Link to="/talent">{t('talent.backToDirectory')}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const whatsapp = whatsappHref(
    data.whatsapp,
    t('talent.whatsappMessage', { name: data.display_name }),
  )
  const phone = telHref(data.phone)
  const skillLabel =
    data.skill?.slug === 'other' && data.custom_skill_text
      ? data.custom_skill_text
      : (data.skill?.name_ar ?? null)

  return (
    <article className="pb-16">
      <div className="container-page pt-10">
        <div className="flex flex-col gap-4 rounded-2xl border border-ink-100 bg-white p-6 shadow-card sm:flex-row sm:items-center">
          <div className="h-28 w-28 shrink-0 overflow-hidden rounded-full border-4 border-white bg-sand-100 shadow-card">
            {data.photo_url ? (
              <img
                src={data.photo_url}
                alt={t('talent.photoAlt', { name: data.display_name })}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <UserRound className="h-12 w-12" aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl sm:text-3xl">{data.display_name}</h1>
              <Badge className="bg-olive-100 text-olive-700">
                <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                {t('business.verified')}
              </Badge>
            </div>

            {data.headline ? <p className="mt-2 text-ink-600">{data.headline}</p> : null}

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-500">
              {data.skill ? (
                <Link
                  to={`/talent?skill=${encodeURIComponent(data.skill.slug)}`}
                  className="font-semibold text-clay-600 hover:underline"
                >
                  {skillLabel}
                </Link>
              ) : null}
              {data.location ? (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-4 w-4" aria-hidden="true" />
                  {data.location.name_ar}
                </span>
              ) : null}
              {data.years_experience !== null ? (
                <span className="ltr-nums">
                  {t('talent.yearsExperience', { count: data.years_experience })}
                </span>
              ) : null}
            </div>
          </div>

          <Button type="button" variant="outline" size="sm" onClick={() => void handleShare()}>
            {copied ? (
              <>
                <Check className="h-4 w-4" aria-hidden="true" />
                {t('business.linkCopied')}
              </>
            ) : (
              <>
                <Share2 className="h-4 w-4" aria-hidden="true" />
                {t('business.share')}
              </>
            )}
          </Button>
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_20rem]">
          <div className="space-y-8">
            {data.bio ? (
              <section aria-labelledby="bio-heading">
                <h2 id="bio-heading" className="mb-3 text-xl">
                  {t('talent.aboutHeading')}
                </h2>
                <p className="whitespace-pre-line leading-relaxed text-ink-700">{data.bio}</p>
              </section>
            ) : null}

            {data.images.length > 0 ? (
              <section aria-labelledby="portfolio-heading">
                <h2 id="portfolio-heading" className="mb-3 text-xl">
                  {t('talent.portfolioHeading')}
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
                        alt={
                          image.caption ??
                          t('talent.portfolioImageAlt', { name: data.display_name })
                        }
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
                  <a
                    href={phone ?? '#'}
                    className="flex items-center gap-3 text-ink-700 hover:text-clay-600"
                  >
                    <Phone className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    <span className="ltr-nums">{data.phone}</span>
                  </a>
                ) : null}

                {data.email ? (
                  <a
                    href={`mailto:${data.email}`}
                    className="flex items-center gap-3 break-all text-ink-700 hover:text-clay-600"
                  >
                    <Mail className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    {data.email}
                  </a>
                ) : null}

                {data.website ? (
                  <a
                    href={data.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 break-all text-ink-700 hover:text-clay-600"
                  >
                    <Globe className="h-5 w-5 shrink-0 text-clay-500" aria-hidden="true" />
                    {data.website}
                  </a>
                ) : null}

                {whatsapp ? (
                  <Button asChild block>
                    <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                      <MessageCircle className="h-4 w-4" aria-hidden="true" />
                      {t('business.whatsappCta')}
                    </a>
                  </Button>
                ) : null}
              </CardBody>
            </Card>

            <Button asChild variant="outline" block>
              <Link to="/talent">{t('talent.backToDirectory')}</Link>
            </Button>
          </aside>
        </div>
      </div>
    </article>
  )
}
