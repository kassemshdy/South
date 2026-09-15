import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { testimonialApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'
import type { OwnerTestimonial, TestimonialStatus } from '@/types/api'

/* PENDING_REVIEW and REJECTED are in these maps only because the type is
   exhaustive: the API does not send either to an owner, since text the
   platform has not cleared is absent from this list rather than shown in a
   state they cannot act on. */
const STATUS_LABEL: Record<TestimonialStatus, TranslationKey> = {
  PENDING_REVIEW: 'testimonials.pendingReview',
  PENDING_OWNER: 'testimonials.pending',
  APPROVED: 'testimonials.approved',
  HIDDEN: 'testimonials.hidden',
  REJECTED: 'testimonials.pendingReview',
}

const STATUS_TONE: Record<TestimonialStatus, string> = {
  PENDING_REVIEW: 'bg-ink-100 text-ink-600',
  PENDING_OWNER: 'bg-wheat-100 text-wheat-700',
  APPROVED: 'bg-olive-100 text-olive-800',
  HIDDEN: 'bg-ink-100 text-ink-600',
  REJECTED: 'bg-ink-100 text-ink-600',
}

/**
 * The owner deciding what appears on their own page.
 *
 * Every state the platform has cleared is shown, not just the ones awaiting
 * a decision: an owner needs to see what is currently displayed in order to
 * take it down, and a hidden testimonial has to stay visible *here* or the
 * only way to find it again would be to have remembered it.
 *
 * What is not here is anything still awaiting review, or refused — the API
 * does not send those to an owner. Being asked to hide abuse means having
 * read it, which is what the platform gate exists to prevent.
 */
export function OwnerTestimonials({ businessId }: { businessId: string }) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()

  const testimonials = useQuery({
    queryKey: queryKeys.myTestimonials(businessId),
    queryFn: () => testimonialApi.listMine(businessId),
  })

  const decide = useMutation({
    mutationFn: ({ id, next }: { id: string; next: 'approve' | 'hide' }) =>
      next === 'approve'
        ? testimonialApi.approve(businessId, id)
        : testimonialApi.hide(businessId, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.myTestimonials(businessId),
      })
      // The public profile carries approved ones, so it is now stale.
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(businessId) })
    },
    onError: (error) =>
      toast.error(
        t('testimonials.updateFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
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
                <Badge className={STATUS_TONE[entry.status]}>
                  {t(STATUS_LABEL[entry.status])}
                </Badge>
                <span className="text-xs text-ink-300">
                  {formatDate(entry.created_at, locale)}
                </span>
              </div>
              <p className="mt-2 leading-relaxed text-ink-700">{entry.body}</p>

              <div className="mt-3 flex flex-wrap gap-2">
                {entry.status === 'APPROVED' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    loading={decide.isPending}
                    onClick={() => decide.mutate({ id: entry.id, next: 'hide' })}
                  >
                    <EyeOff className="h-4 w-4" aria-hidden="true" />
                    {t('testimonials.hide')}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    loading={decide.isPending}
                    onClick={() => decide.mutate({ id: entry.id, next: 'approve' })}
                  >
                    <Eye className="h-4 w-4" aria-hidden="true" />
                    {t('testimonials.approve')}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
