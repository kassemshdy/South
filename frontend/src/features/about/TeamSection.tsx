import { useQuery } from '@tanstack/react-query'
import { UserRound } from 'lucide-react'

import { useI18n } from '@/i18n'
import { teamApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * "Meet the team" at the foot of the about page: up to six photographs,
 * each with its sentence, set by an administrator. Nothing at all until one
 * slot is filled, so the page never shows an empty frame.
 */
export function TeamSection() {
  const { t, locale } = useI18n()
  const team = useQuery({ queryKey: queryKeys.team, queryFn: teamApi.list, staleTime: 10 * 60_000 })
  const members = team.data ?? []
  if (members.length === 0) return null

  return (
    <section aria-labelledby="team-heading" className="mx-auto mt-14 max-w-4xl">
      <h2 id="team-heading" className="text-center text-2xl">
        {t('about.teamHeading')}
      </h2>
      <ul className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-3">
        {members.map((member) => {
          // The reader's language, and the other one rather than nothing.
          const caption =
            (locale === 'ar' ? member.caption_ar : member.caption_en) ??
            member.caption_ar ??
            member.caption_en
          return (
            <li key={member.slot} className="flex flex-col items-center text-center">
              {member.photo_url ? (
                <img
                  src={member.photo_url}
                  alt=""
                  loading="lazy"
                  className="h-32 w-32 rounded-full object-cover shadow-card sm:h-36 sm:w-36"
                />
              ) : (
                <span className="flex h-32 w-32 items-center justify-center rounded-full bg-sand-100 text-sand-500 sm:h-36 sm:w-36">
                  <UserRound className="h-12 w-12" aria-hidden="true" />
                </span>
              )}
              {caption ? (
                <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-ink-700" dir="auto">
                  {caption}
                </p>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
