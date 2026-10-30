import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  BadgeCheck,
  Globe,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Star,
  UserRound,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { BackLink } from '@/components/ui/BackLink'
import { Button } from '@/components/ui/Button'
import { DisplacedBadge } from '@/components/ui/DisplacedBadge'
import { Card, CardBody } from '@/components/ui/Card'
import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { GalleryLightbox } from '@/components/ui/GalleryLightbox'
import { ShareButton } from '@/components/ui/ShareButton'
import { FavouriteButton } from '@/features/favourites/FavouriteButton'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { trackListingView } from '@/services/analytics'
import { useI18n, useT } from '@/i18n'
import { EMPLOYMENT_TYPE_KEYS, PROFICIENCY_KEYS, WORK_MODE_KEYS } from '@/features/talent/labels'
import { FollowLinks } from '@/features/social/FollowLinks'
import { ListingMap } from '@/features/map/ListingMap'
import { googleMapsHref, pinOf } from '@/features/map/types'
import { directoryPath } from '@/features/talent/kind'
import {
  isChipList,
  parseList,
  plainLines,
  textDirection,
  type ParsedList,
} from '@/features/talent/profileText'
import { ServiceRequestForm } from '@/features/talent/ServiceRequestForm'
import { TestimonialForm } from '@/features/testimonials/TestimonialForm'
import { TestimonialList } from '@/features/testimonials/TestimonialList'
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
  // The gallery photo open in the lightbox, if any.
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null)

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
  useEffect(() => {
    if (!data) return
    trackListingView({
      listing_type: data.kind === 'JOB_SEEKER' ? 'job_seeker' : 'service',
      listing: data.slug,
      skill: data.skill?.slug,
      location: data.location?.slug,
    })
  }, [data])

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
            <Link to={directoryPath(data?.kind)}>{t('common.back')}</Link>
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
  const profilePin = pinOf(data.latitude, data.longitude)
  const skillLabel =
    data.skill?.slug === 'other' && data.custom_skill_text
      ? data.custom_skill_text
      : (data.skill?.name_ar ?? null)

  // Short facts read at a glance; long free text reads as a list. Which is
  // which is decided by the field, not by the profile: a degree is a few
  // words wherever it comes from, a training history is never one line.
  // Only what the person filled in is shown.
  const quickFacts: { key: string; label: string; value: string }[] = []
  if (data.work_mode) {
    quickFacts.push({
      key: 'work_mode',
      label: t('talent.workModeLabel'),
      value: t(WORK_MODE_KEYS[data.work_mode]),
    })
  } else if (data.remote_capable) {
    // A profile from before the question was asked.
    quickFacts.push({
      key: 'remote_capable',
      label: t('talent.remoteCapableLabel'),
      value: t('talent.remoteCapableValue'),
    })
  }
  if (data.employment_type) {
    quickFacts.push({
      key: 'employment_type',
      label: t('talent.employmentTypeLabel'),
      value: t(EMPLOYMENT_TYPE_KEYS[data.employment_type]),
    })
  }
  if (data.years_experience !== null) {
    quickFacts.push({
      key: 'years_experience',
      label: t('talent.field.years_experience'),
      value: t('talent.yearsExperience', { count: data.years_experience }),
    })
  }
  if (data.highest_degree) {
    quickFacts.push({
      key: 'highest_degree',
      label: t('talent.degreeLabel'),
      value: data.highest_degree,
    })
  }

  const shortQualifications = (
    [
      ['specialization', 'talent.specializationLabel'],
      ['university', 'talent.universityLabel'],
    ] as const
  ).flatMap(([key, labelKey]) => {
    const value = data[key]
    return value ? [{ key: key as string, label: t(labelKey), value }] : []
  })
  if (data.education_years !== null) {
    shortQualifications.push({
      key: 'education_years',
      label: t('talent.educationYearsLabel'),
      value: t('talent.educationYearsValue', { count: data.education_years }),
    })
  }
  if (data.graduation_date) {
    shortQualifications.push({
      key: 'graduation_date',
      label: t('talent.graduationDateLabel'),
      value: formatDate(data.graduation_date, locale),
    })
  }

  const longQualifications = (
    [
      ['experience', 'talent.experienceLabel'],
      ['professional_training', 'talent.professionalTrainingLabel'],
      ['study_focus', 'talent.studyFocusLabel'],
      ['hobbies', 'talent.hobbiesLabel'],
    ] as const
  ).flatMap(([key, labelKey]) => {
    const value = data[key]
    return value ? [{ key: key as string, label: t(labelKey), list: parseList(value) }] : []
  })

  const services = data.services_offered ? parseList(data.services_offered) : null
  const skills = data.skills_text
    ? isChipList(data.skills_text)
      ? { chips: plainLines(data.skills_text), list: null }
      : { chips: null, list: parseList(data.skills_text) }
    : null

  const hasQualifications =
    shortQualifications.length > 0 ||
    longQualifications.length > 0 ||
    skills !== null ||
    data.languages.length > 0

  const sections = [
    data.bio ? { id: 'about', label: t('talent.aboutHeading') } : null,
    data.youtube_video_id ? { id: 'video', label: t('talent.videoHeading') } : null,
    services ? { id: 'services', label: t('talent.servicesLabel') } : null,
    hasQualifications ? { id: 'qualifications', label: t('talent.professionalHeading') } : null,
    data.images.length > 0 ? { id: 'work', label: t('talent.portfolioHeading') } : null,
    data.kind === 'SERVICE' ? { id: 'reviews', label: t('testimonials.heading') } : null,
  ].filter((section): section is { id: string; label: string } => section !== null)

  /* Default order, most immediate first. The preferred channel is moved to
     the front of this rather than replacing it. WhatsApp's button is in the
     header, so here it is the number, like the phone. */
  const contactEntries: Record<ContactChannel, ReactNode | null> = {
    WHATSAPP:
      whatsapp && data.whatsapp ? (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 text-ink-700 hover:text-brand-700"
        >
          <MessageCircle className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
          <span className="ltr-nums">{data.whatsapp}</span>
        </a>
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

  const hasStickyBar = Boolean(whatsapp || phone)

  return (
    <article className={hasStickyBar ? 'pb-28 lg:pb-16' : 'pb-16'}>
      <div className="container-page pt-10">
        <BackLink fallback={directoryPath(data.kind)} />

        {/* The band is decoration; the card over it is the header. The
            profile's cover when it has one, a brand colour otherwise. */}
        <div className="mt-4">
          {data.cover_url ? (
            <div
              className="h-40 overflow-hidden rounded-3xl bg-brand-800 sm:h-56"
              aria-hidden="true"
            >
              <img src={data.cover_url} alt="" className="h-full w-full object-cover" />
            </div>
          ) : (
            <div className="h-24 rounded-3xl bg-brand-800 sm:h-32" aria-hidden="true" />
          )}
          <div className="relative -mt-16 px-3 sm:-mt-20 sm:px-6">
            <div className="flex flex-col gap-6 rounded-2xl border border-ink-100 bg-white p-5 shadow-card sm:p-7 lg:flex-row lg:items-start">
              <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-start sm:text-start lg:flex-1">
                <div className="h-32 w-32 shrink-0 overflow-hidden rounded-3xl border-4 border-white bg-sand-100 shadow-card sm:h-36 sm:w-36">
                  {data.photo_url ? (
                    <img
                      src={data.photo_url}
                      alt={t('talent.photoAlt', { name: data.display_name })}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sand-500">
                      <UserRound className="h-14 w-14" aria-hidden="true" />
                    </div>
                  )}
                </div>

                {/* The block follows the page (right to left); only
                    owner-authored text is isolated with its own direction. On
                    the whole block, dir="auto" turned a Latin name into a
                    left-to-right header with its details reversed. */}
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
                    <Badge className="bg-olive-100 text-olive-700">
                      <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('business.verified')}
                    </Badge>
                    <DisplacedBadge place={data.displaced_from} />
                  </div>
                  <h1 className="text-2xl leading-tight sm:text-3xl">
                    <bdi>{data.display_name}</bdi>
                  </h1>
                  {skillLabel || data.skill_specialty ? (
                    <p className="text-lg font-semibold text-brand-700">
                      {data.skill ? (
                        <Link
                          to={`${directoryPath(data.kind)}?skill=${encodeURIComponent(data.skill.slug)}`}
                          dir="auto"
                          className="hover:underline"
                        >
                          {skillLabel}
                        </Link>
                      ) : null}
                      {/* The taxonomy value links to a filtered list; the
                          specialty does not, because nothing filters on free
                          text. */}
                      {data.skill && data.skill_specialty ? (
                        <span className="text-ink-300" aria-hidden="true">
                          {' · '}
                        </span>
                      ) : null}
                      {data.skill_specialty ? (
                        <bdi className="font-normal text-ink-600">{data.skill_specialty}</bdi>
                      ) : null}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-sm text-ink-500 sm:justify-start">
                    {data.kind === 'SERVICE' &&
                    data.rating_count > 0 &&
                    data.rating_average !== null ? (
                      <span className="inline-flex items-center gap-1 font-semibold text-ink-700">
                        <Star className="h-4 w-4 fill-amber-400 text-amber-400" aria-hidden="true" />
                        <span className="ltr-nums">
                          {t('testimonials.ratingSummary', {
                            average: Number(data.rating_average).toFixed(1),
                            count: data.rating_count,
                          })}
                        </span>
                      </span>
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
              </div>

              <div className="flex w-full flex-col gap-2 lg:w-80 lg:shrink-0">
                {whatsapp ? (
                  <Button asChild variant="whatsapp" block className="min-h-12 text-base">
                    <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                      <MessageCircle className="h-5 w-5" aria-hidden="true" />
                      {t('business.whatsappCta')}
                    </a>
                  </Button>
                ) : null}
                <div className="grid grid-cols-2 gap-2">
                  {phone ? (
                    <Button asChild variant="outline" block className="px-3">
                      <a href={phone}>
                        <Phone className="h-4 w-4" aria-hidden="true" />
                        {t('business.callCta')}
                      </a>
                    </Button>
                  ) : null}
                  <Button
                    asChild
                    variant="outline"
                    block
                    className={phone ? 'whitespace-nowrap px-3' : 'col-span-2 px-3'}
                  >
                    <a href="#request">{t('serviceRequests.askHeading')}</a>
                  </Button>
                </div>
                <div className="flex justify-center gap-2 lg:justify-end">
                  <ShareButton title={data.display_name} text={data.bio ?? undefined} />
                  <FavouriteButton
                    subject="TALENT"
                    slug={data.slug}
                    title={data.display_name}
                    imageUrl={data.photo_url}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {quickFacts.length > 0 || data.languages.length > 0 ? (
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {quickFacts.map(({ key, label, value }) => (
              <div key={key} className="rounded-xl border border-ink-100 bg-white p-4">
                <dt className="text-xs font-semibold text-ink-500">{label}</dt>
                <dd className="mt-1 font-semibold text-ink-800" dir="auto">
                  {value}
                </dd>
              </div>
            ))}
            {data.languages.length > 0 ? (
              <div className="rounded-xl border border-ink-100 bg-white p-4">
                <dt className="text-xs font-semibold text-ink-500">{t('talent.languagesLabel')}</dt>
                <dd className="mt-1 font-semibold text-ink-800">
                  {data.languages.map((language) => language.name).join(' · ')}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        {sections.length > 1 ? (
          <nav
            aria-label={t('talent.sectionsLabel')}
            className="mt-6 flex gap-2 overflow-x-auto rounded-xl border border-ink-100 bg-white p-2"
          >
            {sections.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className="shrink-0 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-semibold text-ink-700 hover:bg-sand-100 hover:text-brand-800"
              >
                {section.label}
              </a>
            ))}
          </nav>
        ) : null}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_20rem]">
          <div className="min-w-0 space-y-8">
            {data.bio ? (
              <section
                id="about"
                aria-labelledby="bio-heading"
                className="scroll-mt-24 rounded-2xl border border-ink-100 bg-white p-5 sm:p-6"
              >
                <h2 id="bio-heading" className="mb-3 text-xl">
                  {t('talent.aboutHeading')}
                </h2>
                <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                  {data.bio}
                </p>
              </section>
            ) : null}

            {/* After the written bio: a person introducing themselves in their
                own voice belongs where the reader is still deciding whether to
                keep reading. Their own photo is the poster, so no third-party
                request is made until someone taps. */}
            {data.youtube_video_id ? (
              <section id="video" aria-labelledby="video-heading" className="scroll-mt-24">
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

            {services ? (
              <section
                id="services"
                aria-labelledby="services-heading"
                className="scroll-mt-24 rounded-2xl border border-ink-100 bg-white p-5 sm:p-6"
              >
                <h2 id="services-heading" className="mb-1 text-xl">
                  {t('talent.servicesLabel')}
                </h2>
                {services.intro.map((line) => (
                  <p key={line} className="text-sm text-ink-500" dir="auto">
                    {line}
                  </p>
                ))}
                <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                  {services.items.map((item, index) => (
                    <li key={index} className="rounded-xl bg-sand-50 p-4">
                      <p className="font-semibold text-ink-800" dir="auto">
                        {item.main}
                      </p>
                      {item.sub.map((line) => (
                        <p key={line} className="mt-1 text-sm text-ink-500" dir="auto">
                          {line}
                        </p>
                      ))}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {hasQualifications ? (
              <section
                id="qualifications"
                aria-labelledby="professional-heading"
                className="scroll-mt-24 space-y-5 rounded-2xl border border-ink-100 bg-white p-5 sm:p-6"
              >
                <h2 id="professional-heading" className="text-xl">
                  {t('talent.professionalHeading')}
                </h2>
                {shortQualifications.length > 0 ? (
                  <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    {shortQualifications.map(({ key, label, value }) => (
                      <div key={key} className="rounded-xl border border-ink-100 p-3">
                        <dt className="text-xs font-semibold text-ink-500">{label}</dt>
                        <dd className="mt-1 font-semibold text-ink-800" dir="auto">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                ) : null}

                {longQualifications.map(({ key, label, list }) => (
                  <div key={key}>
                    <h3 className="mb-2 text-base font-bold text-brand-800">{label}</h3>
                    <ProfileList list={list} />
                  </div>
                ))}

                {skills ? (
                  <div>
                    <h3 className="mb-2 text-base font-bold text-brand-800">
                      {t('talent.skillsLabel')}
                    </h3>
                    {skills.chips ? (
                      <ul dir={textDirection(skills.chips.join(' '))} className="flex flex-wrap gap-2">
                        {skills.chips.map((chip) => (
                          <li
                            key={chip}
                            dir="auto"
                            className="rounded-full bg-olive-100 px-3 py-1.5 text-sm text-olive-800"
                          >
                            {chip}
                          </li>
                        ))}
                      </ul>
                    ) : skills.list ? (
                      <ProfileList list={skills.list} />
                    ) : null}
                  </div>
                ) : null}

                {data.languages.length > 0 ? (
                  <div>
                    <h3 className="mb-2 text-base font-bold text-brand-800">
                      {t('talent.languagesLabel')}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {data.languages.map((language) => (
                        <Badge key={language.id} className="bg-sand-100 text-ink-700">
                          {language.name}
                          <span className="text-ink-500">
                            {t(PROFICIENCY_KEYS[language.proficiency])}
                          </span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </section>
            ) : null}

            {data.images.length > 0 ? (
              <section id="work" aria-labelledby="portfolio-heading" className="scroll-mt-24">
                <h2 id="portfolio-heading" className="mb-3 text-xl">
                  {t('talent.portfolioHeading')}
                </h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {data.images.map((image, index) => (
                    <button
                      key={image.id}
                      type="button"
                      onClick={() => setGalleryIndex(index)}
                      className="group overflow-hidden rounded-xl border border-ink-100 bg-sand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                    >
                      <img
                        src={image.url}
                        alt={
                          image.caption ??
                          t('talent.portfolioImageAlt', { name: data.display_name })
                        }
                        loading="lazy"
                        className="h-32 w-full object-cover transition-transform duration-300 group-hover:scale-105 sm:h-44"
                      />
                    </button>
                  ))}
                </div>
                <GalleryLightbox
                  title={t('talent.portfolioHeading')}
                  images={data.images}
                  index={galleryIndex}
                  onIndexChange={setGalleryIndex}
                />
              </section>
            ) : null}

            {/* A service only, and always rendered there, as on a business
                page: the form is the point, and the first person who wants
                to leave one must have somewhere to do it. A job application
                takes no testimonials. */}
            {data.kind === 'SERVICE' ? (
              <div id="reviews" className="scroll-mt-24 space-y-8">
                <TestimonialList
                  testimonials={data.testimonials}
                  average={data.rating_average}
                  count={data.rating_count}
                />
                <TestimonialForm slug={data.slug} target="talent" />
              </div>
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

                {/* The pin, and a way to get there from it. */}
                <ListingMap pin={profilePin} />
                {profilePin ? (
                  <Button asChild variant="outline" block>
                    <a href={googleMapsHref(profilePin)} target="_blank" rel="noopener noreferrer">
                      <MapPin className="h-4 w-4" aria-hidden="true" />
                      {t('business.locationCta')}
                    </a>
                  </Button>
                ) : null}
              </CardBody>
            </Card>

            <FollowLinks links={data.social_links ?? []} />

            {/* Beside the WhatsApp button, not instead of it: the message
                gets a faster answer, the stored request is what survives the
                answer not coming. The header's "request" button jumps here. */}
            <div id="request" className="scroll-mt-24">
              <ServiceRequestForm slug={slug} whatsappLink={whatsapp} callLink={phone} />
            </div>

            <Button asChild variant="outline" block>
              <Link to={directoryPath(data?.kind)}>{t('common.back')}</Link>
            </Button>
          </aside>
        </div>
      </div>

      {/* On a phone the header scrolls away; the two ways to reach the person
          stay under the thumb. Short labels, so the header's full ones stay
          the page's only "chat on WhatsApp" and "call now" links. */}
      {hasStickyBar ? (
        <div className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 gap-2 border-t border-ink-100 bg-white/95 px-4 pb-4 pt-3 shadow-lift backdrop-blur lg:hidden">
          {whatsapp ? (
            <Button asChild variant="whatsapp" block className={phone ? 'col-span-2' : 'col-span-3'}>
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-4 w-4" aria-hidden="true" />
                {t('talent.stickyWhatsapp')}
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button asChild variant="outline" block className={whatsapp ? '' : 'col-span-3'}>
              <a href={phone}>
                <Phone className="h-4 w-4" aria-hidden="true" />
                {t('talent.stickyCall')}
              </a>
            </Button>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

/** A long free-text field as a list: one item per entry, each in its own
 *  direction, so an English list reads left-aligned on an Arabic page. */
function ProfileList({ list }: { list: ParsedList }) {
  // One direction for the whole list, so the bullets stay on one side.
  const dir = textDirection(list.items.map((item) => item.main).join(' '))
  return (
    <>
      {list.intro.map((line) => (
        <p key={line} className="mb-1 text-sm text-ink-500" dir="auto">
          {line}
        </p>
      ))}
      <ul
        dir={dir}
        className="list-disc space-y-1.5 ps-5 text-start leading-relaxed text-ink-700 marker:text-brand-500"
      >
        {list.items.map((item, index) => (
          <li key={index}>
            {item.main}
            {item.sub.map((line) => (
              <span key={line} className="block text-sm text-ink-500" dir="auto">
                {line}
              </span>
            ))}
          </li>
        ))}
      </ul>
    </>
  )
}
