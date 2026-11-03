import {
  BadgeCheck,
  Download,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Send,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { BackLink } from '@/components/ui/BackLink'
import { Button } from '@/components/ui/Button'
import { DisplacedBadge } from '@/components/ui/DisplacedBadge'
import { ShareButton } from '@/components/ui/ShareButton'
import { FavouriteButton } from '@/features/favourites/FavouriteButton'
import { MapView } from '@/features/map/MapView'
import { AvailabilityBadge } from '@/features/talent/candidate/AvailabilityBadge'
import { CandidateAvatar } from '@/features/talent/candidate/CandidateAvatar'
import { candidateTitle } from '@/features/talent/candidate/CandidateCard'
import { EmployerRequestForm } from '@/features/talent/candidate/EmployerRequestForm'
import {
  AVAILABILITY_KEYS,
  LEVEL_KEYS,
  WORK_TYPE_KEYS,
} from '@/features/talent/candidate/labels'
import { useI18n, useT } from '@/i18n'
import { publicTalentApi } from '@/services/api/endpoints'
import type { TalentDetail } from '@/types/api'
import { formatDate, telHref, whatsappHref } from '@/utils/format'

const FORM_ID = 'employer-request'
/** The town's area, not the door: about a kilometre and a half around it. */
const AREA_RADIUS_METRES = 1500

function yearOf(iso: string | null): string | null {
  return iso ? iso.slice(0, 4) : null
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-ink-100 pt-6 first:border-t-0 first:pt-0">
      <h2 className="mb-3 text-lg font-bold text-ink-900">{title}</h2>
      {children}
    </section>
  )
}

/**
 * A job seeker's public page (the owners' ticket, 31 Oct 2026): the job they
 * want, whether they can start and their CV first; experience as a dated
 * timeline; contact through WhatsApp, a call, or -- when they keep their
 * number private -- the employer form. Anything without data is left out,
 * never shown as "not specified".
 */
export function CandidateProfile({ data }: { data: TalentDetail }) {
  const t = useT()
  const { locale } = useI18n()

  const whatsapp = whatsappHref(data.whatsapp, t('candidate.whatsappMessage'))
  const phone = telHref(data.phone)
  const numberHidden = !whatsapp && !phone
  const cvHref = data.has_cv ? publicTalentApi.cvUrl(data.slug) : null
  const title = candidateTitle(data)

  const updated = (() => {
    if (!data.updated_at) return null
    const days = Math.floor((Date.now() - new Date(data.updated_at).getTime()) / 86_400_000)
    if (days < 1) return t('candidate.updatedToday')
    // Arabic counts differently for one, two, three to ten, and above.
    if (days === 1) return t('candidate.updatedOneDay')
    if (days === 2) return t('candidate.updatedTwoDays')
    if (days <= 10) return t('candidate.updatedFewDays', { days })
    if (days < 60) return t('candidate.updatedDaysAgo', { days })
    return t('candidate.updatedOn', { date: formatDate(data.updated_at, locale) })
  })()

  const meta = [
    data.years_experience !== null
      ? t('talent.yearsExperience', { count: data.years_experience })
      : null,
    data.location?.name_ar ?? null,
    updated,
  ].filter((part): part is string => Boolean(part))

  const workTypes = data.work_types ?? []
  const workAreas = data.work_areas ?? []
  const tiles = [
    data.desired_title ? { key: 'role', label: t('candidate.tileDesiredRole'), value: data.desired_title } : null,
    workTypes.length > 0
      ? {
          key: 'types',
          label: t('candidate.tileWorkType'),
          value: workTypes.map((type) => t(WORK_TYPE_KEYS[type])).join(t('candidate.listSeparator')),
        }
      : null,
    workAreas.length > 0
      ? {
          key: 'areas',
          label: t('candidate.tileWorkAreas'),
          value: workAreas.map((area) => area.name_ar).join(t('candidate.listSeparator')),
        }
      : null,
    data.availability
      ? { key: 'start', label: t('candidate.tileStart'), value: t(AVAILABILITY_KEYS[data.availability]) }
      : null,
    data.languages.length > 0
      ? {
          key: 'languages',
          label: t('candidate.tileLanguages'),
          value: data.languages.map((language) => language.name).join(t('candidate.listSeparator')),
        }
      : null,
  ].filter((tile): tile is { key: string; label: string; value: string } => tile !== null)

  const experiences = data.experiences ?? []
  const education = data.education ?? []
  // A profile from before the structured sections: its one degree, if any.
  const legacyEducation =
    education.length === 0
      ? [data.highest_degree, data.specialization, data.university, yearOf(data.graduation_date)]
          .filter((part): part is string => Boolean(part))
      : []
  const skills = data.skill_tags ?? []
  const courses = data.courses ?? []

  // The town's area, never the home pin: rounded to about a kilometre.
  const area =
    data.latitude !== null && data.longitude !== null
      ? {
          lat: Math.round(data.latitude * 100) / 100,
          lng: Math.round(data.longitude * 100) / 100,
        }
      : null

  const contactRows: ReactNode[] = []
  if (data.whatsapp || data.phone) {
    const number = data.whatsapp ?? data.phone
    contactRows.push(
      <div key="number" className="flex items-center justify-between gap-3">
        <span className="ltr-nums text-ink-700" dir="ltr">
          {number}
        </span>
        <span className="flex gap-1">
          {whatsapp ? (
            <Button asChild size="icon" variant="ghost" aria-label={t('business.whatsappAria')}>
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-5 w-5 text-olive-700" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button asChild size="icon" variant="ghost" aria-label={t('business.callAria')}>
              <a href={phone}>
                <Phone className="h-5 w-5 text-brand-700" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
        </span>
      </div>,
    )
  }
  if (data.email) {
    contactRows.push(
      <a
        key="email"
        href={`mailto:${data.email}`}
        className="flex items-center gap-2 break-all text-ink-700 hover:text-brand-700"
      >
        <Mail className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
        {data.email}
      </a>,
    )
  }

  const scrollToForm = () =>
    document.getElementById(FORM_ID)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <article className="pb-28 lg:pb-16">
      <div className="container-page pt-8">
        <BackLink fallback="/jobs" />

        {/* Header: who, the job they want, and how to reach them. */}
        <header className="mt-4 rounded-2xl border border-ink-100 bg-white p-5 shadow-card sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <CandidateAvatar
              name={data.display_name}
              photoUrl={data.photo_url}
              className="mx-auto h-24 w-24 border-2 border-sea-300 sm:mx-0 sm:h-28 sm:w-28"
              textClassName="text-3xl"
            />
            <div className="min-w-0 flex-1 space-y-1.5 text-center sm:text-start">
              <h1 className="flex flex-wrap items-center justify-center gap-2 text-2xl leading-tight sm:justify-start sm:text-3xl">
                <bdi>{data.display_name}</bdi>
                {data.id_verified ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-sea-100 px-2.5 py-1 text-xs font-semibold text-sea-700">
                    <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    {t('candidate.verifiedId')}
                  </span>
                ) : null}
              </h1>
              {title ? (
                <p className="text-lg font-semibold text-brand-700" dir="auto">
                  {title}
                </p>
              ) : null}
              <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-sm text-ink-500 sm:justify-start">
                <AvailabilityBadge availability={data.availability} />
                {meta.map((part) => (
                  <span key={part} className="ltr-nums">
                    · {part}
                  </span>
                ))}
              </div>
              <DisplacedBadge place={data.displaced_from} className="mx-auto sm:mx-0" />
            </div>

            <div className="flex w-full flex-col gap-2 sm:w-64">
              {numberHidden ? (
                <Button size="lg" block onClick={scrollToForm}>
                  <Send className="h-5 w-5" aria-hidden="true" />
                  {t('candidate.requestContact')}
                </Button>
              ) : (
                <>
                  {whatsapp ? (
                    <Button asChild size="lg" block className="bg-olive-600 hover:bg-olive-700">
                      <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                        <MessageCircle className="h-5 w-5" aria-hidden="true" />
                        {t('candidate.whatsappAction')}
                      </a>
                    </Button>
                  ) : null}
                  {phone ? (
                    <Button asChild variant="outline" block>
                      <a href={phone}>
                        <Phone className="h-4 w-4" aria-hidden="true" />
                        {t('candidate.callAction')}
                      </a>
                    </Button>
                  ) : null}
                </>
              )}
              {cvHref ? (
                <Button asChild variant="outline" block className="border-sea-500 text-sea-700">
                  <a href={cvHref} download>
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {t('candidate.downloadCv')}
                  </a>
                </Button>
              ) : null}
              <div className="grid grid-cols-2 gap-2">
                <ShareButton title={data.display_name} text={title ?? undefined} block />
                <FavouriteButton
                  subject="TALENT"
                  slug={data.slug}
                  title={data.display_name}
                  imageUrl={data.photo_url}
                  block
                />
              </div>
            </div>
          </div>
        </header>

        {tiles.length > 0 ? (
          <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {tiles.map((tile) => (
              <li key={tile.key} className="rounded-xl border border-ink-100 bg-white p-4">
                <p className="text-xs font-semibold text-ink-500">{tile.label}</p>
                <p className="mt-1 font-semibold text-ink-900" dir="auto">
                  {tile.value}
                </p>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-6 rounded-2xl border border-ink-100 bg-white p-5 sm:p-6">
            {data.bio ? (
              <Section title={t('candidate.sectionAbout')}>
                <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                  {data.bio}
                </p>
              </Section>
            ) : null}

            {experiences.length > 0 ? (
              <Section title={t('candidate.sectionExperience')}>
                <ol className="relative space-y-5 border-s-2 border-sea-300 ps-5">
                  {experiences.map((entry, index) => {
                    const from = yearOf(entry.start_date)
                    const to = entry.is_current ? t('candidate.present') : yearOf(entry.end_date)
                    const dates = from && to && from !== to ? `${from} – ${to}` : (from ?? to)
                    const where = [dates, entry.town].filter(Boolean).join(' · ')
                    return (
                      <li key={entry.id} className="relative">
                        <span
                          className={`absolute -start-[1.6rem] top-1 h-3.5 w-3.5 rounded-full border-2 border-sea-500 ${index === 0 ? 'bg-sea-500' : 'bg-white'}`}
                          aria-hidden="true"
                        />
                        <p className="font-semibold text-ink-900" dir="auto">
                          {[entry.title, entry.employer].filter(Boolean).join(' · ')}
                        </p>
                        {where ? <p className="ltr-nums text-sm text-ink-500">{where}</p> : null}
                        {entry.description ? (
                          <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-ink-700" dir="auto">
                            {entry.description}
                          </p>
                        ) : null}
                      </li>
                    )
                  })}
                </ol>
              </Section>
            ) : null}

            {education.length > 0 || legacyEducation.length > 0 ? (
              <Section title={t('candidate.sectionEducation')}>
                <ul className="space-y-2">
                  {education.map((row) => (
                    <li key={row.id} className="text-ink-700" dir="auto">
                      {[row.degree, row.field, row.institution, row.graduation_year]
                        .filter((part) => part !== null && part !== '')
                        .join(' · ')}
                    </li>
                  ))}
                  {legacyEducation.length > 0 ? (
                    <li className="text-ink-700" dir="auto">
                      {legacyEducation.join(' · ')}
                    </li>
                  ) : null}
                </ul>
              </Section>
            ) : null}

            {skills.length > 0 ? (
              <Section title={t('candidate.sectionSkills')}>
                <ul className="flex flex-wrap gap-2">
                  {skills.map((skill) => (
                    <li
                      key={skill}
                      className="rounded-full border border-sea-300 bg-sea-100/50 px-3 py-1 text-sm font-medium text-sea-700"
                      dir="auto"
                    >
                      {skill}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {courses.length > 0 ? (
              <Section title={t('candidate.sectionCourses')}>
                <ul className="space-y-2">
                  {courses.map((course) => (
                    <li key={course.id} className="text-ink-700" dir="auto">
                      {[course.name, course.issuer, course.year]
                        .filter((part) => part !== null && part !== '')
                        .join(' · ')}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {data.languages.length > 0 ? (
              <Section title={t('candidate.sectionLanguages')}>
                <ul className="flex flex-wrap gap-2">
                  {data.languages.map((language) => (
                    <li key={language.id} className="rounded-lg bg-sand-100 px-3 py-1.5 text-sm text-ink-700">
                      <bdi>{language.name}</bdi> · {t(LEVEL_KEYS[language.proficiency])}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}
          </div>

          <aside className="space-y-4">
            {contactRows.length > 0 ? (
              <div className="space-y-3 rounded-2xl border border-ink-100 bg-white p-5">
                <h2 className="font-bold text-ink-900">{t('candidate.contactHeading')}</h2>
                {contactRows}
              </div>
            ) : null}

            {area ? (
              <figure className="overflow-hidden rounded-2xl border border-ink-100 bg-white">
                <MapView
                  value={area}
                  areaRadius={AREA_RADIUS_METRES}
                  label={t('candidate.mapCaption')}
                  className="h-48 w-full"
                />
                <figcaption className="flex items-center gap-1.5 p-3 text-sm text-ink-500">
                  <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {data.location?.name_ar ? `${data.location.name_ar} · ` : ''}
                  {t('candidate.mapCaption')}
                </figcaption>
              </figure>
            ) : null}

            <EmployerRequestForm slug={data.slug} id={FORM_ID} />
          </aside>
        </div>
      </div>

      {/* Phones: the two actions an employer came for, always in reach. */}
      <div className="fixed inset-x-0 bottom-0 z-30 flex gap-2 border-t border-ink-100 bg-white/95 p-3 backdrop-blur lg:hidden">
        {whatsapp ? (
          <Button asChild block className="bg-olive-600 hover:bg-olive-700">
            <a href={whatsapp} target="_blank" rel="noopener noreferrer">
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              {t('candidate.barWhatsapp')}
            </a>
          </Button>
        ) : (
          <Button block onClick={scrollToForm}>
            <Send className="h-4 w-4" aria-hidden="true" />
            {t('candidate.requestContact')}
          </Button>
        )}
        {cvHref ? (
          <Button asChild block variant="outline">
            <a href={cvHref} download>
              <Download className="h-4 w-4" aria-hidden="true" />
              {t('candidate.barCv')}
            </a>
          </Button>
        ) : null}
      </div>
    </article>
  )
}
