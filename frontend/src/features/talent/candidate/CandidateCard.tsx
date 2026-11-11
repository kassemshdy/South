import { Fragment } from 'react'
import { BadgeCheck, FileText, MapPin, MessageCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { DisplacedBadge } from '@/components/ui/DisplacedBadge'
import { AvailabilityBadge } from '@/features/talent/candidate/AvailabilityBadge'
import { EDUCATION_KEYS } from '@/features/talent/candidate/labels'
import { useT } from '@/i18n'
import type { TalentSummary } from '@/types/api'
import { whatsappHref } from '@/utils/format'

/** The job asked for, else the trade in their words, else the skill. */
export function candidateTitle(talent: TalentSummary): string | null {
  if (talent.desired_title) return talent.desired_title
  if (talent.skill_specialty) return talent.skill_specialty
  if (talent.skill?.slug === 'other') return talent.custom_skill_text
  return talent.skill?.name_ar ?? null
}

/**
 * A job seeker in the candidate directory: what an employer decides on at a
 * glance -- the job they want, whether they can start, how much experience
 * and schooling, and their first few skills.
 */
export function CandidateCard({ talent }: { talent: TalentSummary }) {
  const t = useT()
  const profileUrl = `/talent/${encodeURIComponent(talent.slug)}`
  const title = candidateTitle(talent)
  const tags = talent.skill_tags ?? []
  const shown = tags.slice(0, 3)
  const whatsapp = whatsappHref(talent.whatsapp, t('candidate.whatsappMessage'))

  const meta = [
    talent.years_experience !== null
      ? t('talent.yearsExperience', { count: talent.years_experience })
      : null,
    talent.education_level ? t(EDUCATION_KEYS[talent.education_level]) : null,
  ].filter((part): part is string => Boolean(part))

  return (
    <article className="group flex flex-col rounded-2xl border border-ink-100 bg-white p-5 shadow-card transition-shadow hover:shadow-lift">
      {/* No photo or initials on the card (the owners' request, 11 Nov
          2026): the name, the job wanted and the facts are what an
          employer scans. The profile page keeps the photo. */}
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-1.5 text-lg font-bold text-ink-900">
            <Link to={profileUrl} className="truncate transition-colors hover:text-brand-700">
              <bdi>{talent.display_name}</bdi>
            </Link>
            {talent.id_verified ? (
              <BadgeCheck
                className="h-4 w-4 shrink-0 text-sea-500"
                aria-label={t('candidate.verifiedId')}
              />
            ) : null}
          </h3>
          {title ? (
            <p className="mt-0.5 font-semibold text-brand-700" dir="auto">
              {title}
            </p>
          ) : null}
          <AvailabilityBadge availability={talent.availability} className="mt-2" />
        </div>
      </div>

      {meta.length > 0 || talent.location ? (
        <p className="mt-4 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-ink-500">
          {meta.map((part, index) => (
            <Fragment key={part}>
              {index > 0 ? <span aria-hidden="true">·</span> : null}
              <span className="ltr-nums">{part}</span>
            </Fragment>
          ))}
          {talent.location ? (
            <span className="inline-flex items-center gap-1">
              {meta.length > 0 ? <span aria-hidden="true">·</span> : null}
              <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {talent.location.name_ar}
            </span>
          ) : null}
        </p>
      ) : null}
      <DisplacedBadge place={talent.displaced_from} className="mt-2 self-start" />

      {shown.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {shown.map((tag) => (
            <li
              key={tag}
              className="rounded-full border border-sea-300 bg-sea-100/50 px-2.5 py-0.5 text-xs font-medium text-sea-700"
              dir="auto"
            >
              {tag}
            </li>
          ))}
          {tags.length > shown.length ? (
            <li className="rounded-full bg-sand-100 px-2.5 py-0.5 text-xs font-medium text-ink-700">
              {t('candidate.moreSkills', { count: tags.length - shown.length })}
            </li>
          ) : null}
        </ul>
      ) : null}

      <div className="mt-auto flex items-center gap-2 pt-4">
        <Button asChild size="sm" variant="outline" block>
          <Link to={profileUrl}>{t('talent.viewProfile')}</Link>
        </Button>
        {talent.has_cv ? (
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-ink-500"
            title={t('candidate.cvAvailable')}
          >
            <FileText className="h-4 w-4" aria-label={t('candidate.cvAvailable')} />
          </span>
        ) : null}
        {whatsapp ? (
          <Button asChild size="sm" variant="ghost" aria-label={t('business.whatsappAria')}>
            <a href={whatsapp} target="_blank" rel="noreferrer noopener">
              <MessageCircle className="h-4 w-4 text-olive-700" aria-hidden="true" />
            </a>
          </Button>
        ) : null}
      </div>
    </article>
  )
}
