import { MapPin, MessageCircle, Phone, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import type { TalentSummary } from '@/types/api'

export function TalentCard({ talent }: { talent: TalentSummary }) {
  const t = useT()
  const profileUrl = `/talent/${encodeURIComponent(talent.slug)}`
  // An "Other" profile shows the person's own words; every other profile shows
  // the skill name, so the badge is never the useless literal "Other".
  const skillLabel =
    talent.skill?.slug === 'other' && talent.custom_skill_text
      ? talent.custom_skill_text
      : (talent.skill?.name_ar ?? null)

  return (
    <article className="group flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift">
      <div className="flex items-start gap-4 p-5">
        <Link to={profileUrl} className="shrink-0" tabIndex={-1} aria-hidden="true">
          <div className="h-16 w-16 overflow-hidden rounded-full bg-sand-100">
            {talent.photo_url ? (
              <img
                src={talent.photo_url}
                alt=""
                loading="lazy"
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <UserRound className="h-8 w-8" aria-hidden="true" />
              </div>
            )}
          </div>
        </Link>

        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-bold text-ink-900">
            <Link to={profileUrl} className="transition-colors hover:text-clay-600">
              {talent.display_name}
            </Link>
          </h3>
          {talent.headline ? (
            <p className="mt-1 line-clamp-2 text-sm text-ink-500">{talent.headline}</p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-1 flex-col px-5 pb-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {skillLabel ? <Badge className="bg-sand-100 text-clay-700">{skillLabel}</Badge> : null}
          {talent.years_experience !== null ? (
            <span className="ltr-nums text-sm text-ink-500">
              {t('talent.yearsExperience', { count: talent.years_experience })}
            </span>
          ) : null}
        </div>

        {talent.location ? (
          <p className="flex items-center gap-1 text-sm text-ink-500">
            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {talent.location.name_ar}
          </p>
        ) : null}

        <div className="mt-auto flex gap-2 pt-4">
          <Button asChild size="sm" variant="outline" block>
            <Link to={profileUrl}>{t('talent.viewProfile')}</Link>
          </Button>
          {talent.whatsapp ? (
            <Button asChild size="sm" variant="ghost" aria-label={t('business.whatsappAria')}>
              <a
                href={`https://wa.me/${talent.whatsapp.replace(/\D/g, '')}`}
                target="_blank"
                rel="noreferrer noopener"
              >
                <MessageCircle className="h-4 w-4" aria-hidden="true" />
              </a>
            </Button>
          ) : talent.phone ? (
            <Button asChild size="sm" variant="ghost" aria-label={t('business.callAria')}>
              <a href={`tel:${talent.phone}`}>
                <Phone className="h-4 w-4" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
        </div>
      </div>
    </article>
  )
}
