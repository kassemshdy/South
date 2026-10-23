import { useQuery } from '@tanstack/react-query'

import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useI18n } from '@/i18n'
import { testimonialApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'
import type { OwnerTestimonial } from '@/types/api'
import { Stars } from '@/features/testimonials/Stars'

/** Whose testimonials: one of the account's businesses, or its profile. */
export type OwnerTestimonialsSource = { kind: 'business'; id: string } | { kind: 'talent' }

/**
 * What is published on the owner's own page, read-only.
 *
 * The owners decided (round 3) that an administrator's approval alone
 * publishes a testimonial: the listing's owner neither approves nor hides.
 * So this is the page as a visitor sees it, and the API sends nothing that
 * is still awaiting review or was refused -- handing an owner unread text
 * aimed at them is what the review exists to prevent.
 */
export function OwnerTestimonials({ source }: { source: OwnerTestimonialsSource }) {
  const { t, locale } = useI18n()

  const testimonials = useQuery({
    queryKey:
      source.kind === 'business'
        ? queryKeys.myTestimonials(source.id)
        : queryKeys.myTalentTestimonials,
    queryFn: () =>
      source.kind === 'business'
        ? testimonialApi.listMine(source.id)
        : testimonialApi.listMyTalent(),
  })

  if (testimonials.isLoading) return <Skeleton className="h-40 rounded-2xl" />
  if (testimonials.isError) {
    return (
      <ErrorState
        error={testimonials.error}
        onRetry={() => void testimonials.refetch()}
      />
    )
  }

  const entries: OwnerTestimonial[] = testimonials.data ?? []

  return (
    <div>
      <h3 className="font-bold">{t('testimonials.ownerHeading')}</h3>
      <p className="mt-1 text-sm text-ink-500">{t('testimonials.ownerIntro')}</p>

      {entries.length === 0 ? (
        <p className="mt-4 rounded-xl bg-sand-50 p-4 text-sm text-ink-500">
          {t('testimonials.ownerEmpty')}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {entries.map((entry) => (
            <li key={entry.id} className="rounded-xl border border-ink-100 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{entry.author_name}</span>
                <span className="text-xs text-ink-300">
                  {formatDate(entry.created_at, locale)}
                </span>
              </div>
              {entry.rating ? <Stars value={entry.rating} className="mt-2" /> : null}
              <p className="mt-2 leading-relaxed text-ink-700">{entry.body}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
