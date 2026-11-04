import { Fragment, type ReactNode } from 'react'
import { BadgeCheck, MapPin, MessageCircle, Star, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

import { CardImage } from '@/components/ui/CardImage'
import { DisplacedBadge } from '@/components/ui/DisplacedBadge'
import { CategoryIcon } from '@/features/home/categoryIcon'
import { CandidateCard } from '@/features/talent/candidate/CandidateCard'
import { useT } from '@/i18n'
import type { TalentSummary } from '@/types/api'
import { formatPrice, whatsappHref } from '@/utils/format'

export function TalentCard({ talent }: { talent: TalentSummary }) {
  // A job seeker gets the candidate card wherever a talent card is drawn
  // (the directory, the homepage, search): initials, never the silhouette.
  if (talent.kind === 'JOB_SEEKER') return <CandidateCard talent={talent} />
  return <ServiceCard talent={talent} />
}

/** The skill as a visitor reads it: an "Other" profile's own words. */
export function serviceSkillLabel(talent: TalentSummary): string | null {
  return talent.skill?.slug === 'other' && talent.custom_skill_text
    ? talent.custom_skill_text
    : (talent.skill?.name_ar ?? null)
}

/**
 * What the person offers, in one line: their own narrower description of the
 * work when they wrote one, the skill otherwise -- never the degree, which
 * says what someone studied rather than what they will do for you.
 */
export function serviceHeadline(talent: TalentSummary): string | null {
  return talent.skill_specialty || serviceSkillLabel(talent)
}

/**
 * A service provider in the directory, laid out so a visitor can judge them
 * from the card alone (the owners' services redesign, 31 Oct 2026): their
 * work across the top, the person over it, what they offer, then the proof --
 * stars, place, years -- and one tap to WhatsApp.
 */
function ServiceCard({ talent }: { talent: TalentSummary }) {
  const t = useT()
  const profileUrl = `/talent/${encodeURIComponent(talent.slug)}`
  const skillLabel = serviceSkillLabel(talent)
  const headline = serviceHeadline(talent)
  const whatsapp = whatsappHref(
    talent.whatsapp,
    headline
      ? t('talent.whatsappInquiry', { service: headline })
      : t('talent.whatsappMessage', { name: talent.display_name }),
  )
  const rated = talent.rating_count > 0 && talent.rating_average !== null
  const startingPrice = formatPrice(talent.starting_price ?? null, talent.starting_price_currency ?? 'USD')

  const meta: { key: string; node: ReactNode }[] = []
  if (rated) {
    meta.push({
      key: 'rating',
      node: (
        <span className="inline-flex items-center gap-1 font-semibold text-ink-700">
          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" aria-hidden="true" />
          <span className="ltr-nums">
            {t('testimonials.ratingSummary', {
              average: Number(talent.rating_average).toFixed(1),
              count: talent.rating_count,
            })}
          </span>
        </span>
      ),
    })
  }
  if (talent.location) {
    meta.push({
      key: 'location',
      node: (
        <span className="inline-flex items-center gap-1">
          <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {talent.location.name_ar}
        </span>
      ),
    })
  }
  if (talent.years_experience !== null) {
    meta.push({
      key: 'years',
      node: (
        <span className="ltr-nums">
          {t('talent.yearsExperience', { count: talent.years_experience })}
        </span>
      ),
    })
  }

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift">
      {/* The work, 16:9. Without a cover, the category's colour and icon
          rather than an empty grey box. */}
      <div className="relative aspect-video bg-sand-100" aria-hidden="true">
        {talent.cover_url ? (
          <img
            src={talent.cover_url}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-sand-100 to-olive-100 text-brand-700/40">
            <CategoryIcon name={talent.skill?.icon} className="h-12 w-12" />
          </div>
        )}
        <div className="absolute -bottom-8 start-5 h-16 w-16 overflow-hidden rounded-full border-4 border-white bg-sand-100 shadow-card">
          {talent.photo_url ? (
            <CardImage
              src={talent.photo_url}
              thumbSrc={talent.photo_thumb_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sand-500">
              <UserRound className="h-7 w-7" />
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col px-5 pb-5 pt-10">
        <h3 className="flex items-center gap-1.5 text-lg font-bold text-ink-900">
          {/* The whole card opens the profile: this link's hit area is
              stretched over it, and the WhatsApp button sits above that. */}
          <Link
            to={profileUrl}
            className="truncate transition-colors after:absolute after:inset-0 after:content-[''] hover:text-brand-700"
          >
            <bdi>{talent.display_name}</bdi>
          </Link>
          {talent.id_verified ? (
            <BadgeCheck
              className="h-4 w-4 shrink-0 text-olive-600"
              aria-label={t('business.verified')}
            />
          ) : null}
        </h3>
        {headline ? (
          <p className="mt-0.5 line-clamp-2 font-semibold text-brand-700" dir="auto">
            {headline}
          </p>
        ) : null}

        {meta.length > 0 ? (
          <p className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-ink-500">
            {meta.map((part, index) => (
              <Fragment key={part.key}>
                {index > 0 ? <span aria-hidden="true">·</span> : null}
                {part.node}
              </Fragment>
            ))}
          </p>
        ) : null}

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {skillLabel && skillLabel !== headline ? (
            <span
              className="rounded-full bg-sand-100 px-2.5 py-0.5 text-xs font-medium text-brand-700"
              dir="auto"
            >
              {skillLabel}
            </span>
          ) : null}
          <DisplacedBadge place={talent.displaced_from} />
        </div>

        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          {/* The lowest priced service, the one figure a visitor compares
              before opening a profile; "view profile" when nothing is priced. */}
          {startingPrice ? (
            <span className="text-sm text-ink-500">
              {t('serviceOffers.startingFrom')}{' '}
              <span className="ltr-nums font-bold text-ink-900" dir="ltr">
                {startingPrice}
              </span>
            </span>
          ) : (
            <span className="text-sm font-semibold text-brand-700">{t('talent.viewProfile')}</span>
          )}
          {whatsapp ? (
            <a
              href={whatsapp}
              target="_blank"
              rel="noreferrer noopener"
              aria-label={t('business.whatsappAria')}
              className="relative z-10 flex h-10 w-10 items-center justify-center rounded-full bg-olive-100 text-olive-700 transition-colors hover:bg-olive-200"
            >
              <MessageCircle className="h-5 w-5" aria-hidden="true" />
            </a>
          ) : null}
        </div>
      </div>
    </article>
  )
}
