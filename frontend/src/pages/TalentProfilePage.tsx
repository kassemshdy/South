import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  BadgeCheck,
  Globe,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  UserRound,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { ShareButton } from '@/components/ui/ShareButton'
import { FavouriteButton } from '@/features/favourites/FavouriteButton'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT } from '@/i18n'
import { EMPLOYMENT_TYPE_KEYS, PROFICIENCY_KEYS } from '@/features/talent/labels'
import { ServiceRequestForm } from '@/features/talent/ServiceRequestForm'
import { publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ContactChannel } from '@/types/api'
import { formatDate, telHref, whatsappHref } from '@/utils/format'

/** Default order, most immediate first; a preference moves one to the front. */
const DEFAULT_CONTACT_ORDER: ContactChannel[] = ['PHONE', 'EMAIL', 'WEBSITE', 'WHATSAPP']

export function TalentProfilePage() {
  const { slug = '' } = useParams()
  const t = useT()
  const { locale } = useI18n()

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
    description: data?.bio ?? undefined,
    image: data?.photo_url ?? null,
    canonicalPath: `/talent/${encodeURIComponent(slug)}`,
  })

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

  // Only the fields the person actually filled in get a row — an empty
  // definition list would otherwise render as a box of headings.
  const textFields = (
    [
      ['highest_degree', 'talent.degreeLabel'],
      ['specialization', 'talent.specializationLabel'],
      ['university', 'talent.universityLabel'],
      ['study_focus', 'talent.studyFocusLabel'],
      ['experience', 'talent.experienceLabel'],
      ['professional_training', 'talent.professionalTrainingLabel'],
      ['skills_text', 'talent.skillsLabel'],
      ['services_offered', 'talent.servicesLabel'],
      ['hobbies', 'talent.hobbiesLabel'],
    ] as const
  ).flatMap(([key, labelKey]) => {
    const value = data[key]
    return value ? [{ key: key as string, label: t(labelKey), value }] : []
  })

  const derivedFields: { key: string; label: string; value: string }[] = []
  if (data.education_years !== null) {
    derivedFields.push({
      key: 'education_years',
      label: t('talent.educationYearsLabel'),
      value: t('talent.educationYearsValue', { count: data.education_years }),
    })
  }
  if (data.graduation_date) {
    derivedFields.push({
      key: 'graduation_date',
      label: t('talent.graduationDateLabel'),
      value: formatDate(data.graduation_date, locale),
    })
  }
  if (data.employment_type) {
    derivedFields.push({
      key: 'employment_type',
      label: t('talent.employmentTypeLabel'),
      value: t(EMPLOYMENT_TYPE_KEYS[data.employment_type]),
    })
  }
  if (data.remote_capable) {
    derivedFields.push({
      key: 'remote_capable',
      label: t('talent.remoteCapableLabel'),
      value: t('talent.remoteCapableValue'),
    })
  }
  const professional = [...textFields, ...derivedFields]

  /* Default order, most immediate first. The preferred channel is moved to
     the front of this rather than replacing it. */
  const contactEntries: Record<ContactChannel, ReactNode | null> = {
    WHATSAPP: whatsapp ? (
      <Button asChild block>
        <a href={whatsapp} target="_blank" rel="noopener noreferrer">
          <MessageCircle className="h-4 w-4" aria-hidden="true" />
          {t('business.whatsappCta')}
        </a>
      </Button>
    ) : null,
    PHONE: data.phone ? (
      <a
        href={phone ?? '#'}
        className="flex items-center gap-3 text-ink-700 hover:text-brand-700"
      >
        <Phone className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
        <span className="ltr-nums">{data.phone}</span>
      </a>
    ) : null,
    EMAIL: data.email ? (
      <a
        href={`mailto:${data.email}`}
        className="flex items-center gap-3 break-all text-ink-700 hover:text-brand-700"
      >
        <Mail className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
        {data.email}
      </a>
    ) : null,
    WEBSITE: data.website ? (
      <a
        href={data.website}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 break-all text-ink-700 hover:text-brand-700"
      >
        <Globe className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
        {data.website}
      </a>
    ) : null,
  }

  const contactOrder = data.preferred_contact
    ? [
        data.preferred_contact,
        ...DEFAULT_CONTACT_ORDER.filter((channel) => channel !== data.preferred_contact),
      ]
    : DEFAULT_CONTACT_ORDER


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

          {/* Owner-authored text carries its own direction — see BusinessCard. */}
          <div className="min-w-0 flex-1" dir="auto">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl sm:text-3xl">{data.display_name}</h1>
              <Badge className="bg-olive-100 text-olive-700">
                <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                {t('business.verified')}
              </Badge>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-500">
              {data.skill ? (
                <Link
                  to={`/talent?skill=${encodeURIComponent(data.skill.slug)}`}
                  className="font-semibold text-brand-700 hover:underline"
                >
                  {skillLabel}
                </Link>
              ) : null}
              {/* The taxonomy value links to a filtered list; the specialty
                  does not, because nothing filters on free text. */}
              {data.skill_specialty ? (
                <span className="text-ink-500">{data.skill_specialty}</span>
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

          <div className="flex shrink-0 gap-2">
            <ShareButton title={data.display_name} text={data.bio ?? undefined} />
            <FavouriteButton
              subject="TALENT"
              slug={data.slug}
              title={data.display_name}
              imageUrl={data.photo_url}
            />
          </div>
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_20rem]">
          <div className="space-y-8">
            {data.bio ? (
              <section aria-labelledby="bio-heading">
                <h2 id="bio-heading" className="mb-3 text-xl">
                  {t('talent.aboutHeading')}
                </h2>
                <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                  {data.bio}
                </p>
              </section>
            ) : null}

            {/* After the written bio and before the credentials table: a
                person introducing themselves in their own voice belongs where
                the reader is still deciding whether to keep reading. Their
                own photo is the poster, so no third-party request is made
                until someone taps. */}
            {data.youtube_video_id ? (
              <section aria-labelledby="video-heading">
                <h2 id="video-heading" className="mb-3 text-xl">
                  {t('talent.videoHeading')}
                </h2>
                <YouTubePlayer
                  videoId={data.youtube_video_id}
                  poster={data.photo_url}
                  title={data.display_name}
                  playLabel={t('video.playAria')}
                />
              </section>
            ) : null}

            {professional.length > 0 || data.languages.length > 0 ? (
              <section aria-labelledby="professional-heading">
                <h2 id="professional-heading" className="mb-3 text-xl">
                  {t('talent.professionalHeading')}
                </h2>
                <dl className="grid gap-4 rounded-2xl border border-ink-100 bg-white p-5 shadow-card sm:grid-cols-2">
                  {professional.map(({ key, label, value }) => (
                    <div key={key}>
                      <dt className="text-sm font-semibold text-ink-500">{label}</dt>
                      <dd className="mt-1 whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                        {value}
                      </dd>
                    </div>
                  ))}
                  {data.languages.length > 0 ? (
                    <div className="sm:col-span-2">
                      <dt className="text-sm font-semibold text-ink-500">
                        {t('talent.languagesLabel')}
                      </dt>
                      <dd className="mt-2 flex flex-wrap gap-2">
                        {data.languages.map((language) => (
                          <Badge key={language.id} className="bg-sand-100 text-ink-700">
                            {language.name}
                            <span className="text-ink-500">
                              {t(PROFICIENCY_KEYS[language.proficiency])}
                            </span>
                          </Badge>
                        ))}
                      </dd>
                    </div>
                  ) : null}
                </dl>
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

                {/* Ordered, not filtered: everything the person filled in is
                    here, and `preferred_contact` only decides which comes
                    first. A profile offering four ways to be reached is
                    really offering none — a visitor takes the first one,
                    which may be the one nobody answers. */}
                {contactOrder.map((channel) => {
                  const entry = contactEntries[channel]
                  if (!entry) return null
                  return (
                    <div key={channel} className="space-y-1">
                      {channel === data.preferred_contact ? (
                        <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                          {t('talent.preferredBadge')}
                        </p>
                      ) : null}
                      {entry}
                    </div>
                  )
                })}
              </CardBody>
            </Card>

            {/* Beside the WhatsApp button, not instead of it: the message
                gets a faster answer, the stored request is what survives the
                answer not coming. */}
            <ServiceRequestForm slug={slug} />

            <Button asChild variant="outline" block>
              <Link to="/talent">{t('talent.backToDirectory')}</Link>
            </Button>
          </aside>
        </div>
      </div>
    </article>
  )
}
