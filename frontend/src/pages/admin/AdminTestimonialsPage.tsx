import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminTestimonial, TestimonialStatus } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/format'

type Filter = TestimonialStatus | 'ALL'

/** Awaiting review first: it is the only one with work waiting in it. */
const FILTERS: { value: Filter; labelKey: TranslationKey }[] = [
  { value: 'PENDING_REVIEW', labelKey: 'admin.testimonialFilterPendingReview' },
  { value: 'PENDING_OWNER', labelKey: 'admin.testimonialFilterPendingOwner' },
  { value: 'APPROVED', labelKey: 'admin.testimonialFilterApproved' },
  { value: 'HIDDEN', labelKey: 'admin.testimonialFilterHidden' },
  { value: 'REJECTED', labelKey: 'admin.testimonialFilterRejected' },
  { value: 'ALL', labelKey: 'admin.testimonialFilterAll' },
]

const STATUS_STYLES: Record<TestimonialStatus, string> = {
  PENDING_REVIEW: 'bg-clay-100 text-clay-700',
  PENDING_OWNER: 'bg-sand-100 text-clay-700',
  APPROVED: 'bg-olive-100 text-olive-700',
  HIDDEN: 'bg-ink-100 text-ink-700',
  REJECTED: 'bg-ink-100 text-ink-500',
}

const STATUS_LABELS: Record<TestimonialStatus, TranslationKey> = {
  PENDING_REVIEW: 'admin.testimonialStatusPendingReview',
  PENDING_OWNER: 'admin.testimonialStatusPendingOwner',
  APPROVED: 'admin.testimonialStatusApproved',
  HIDDEN: 'admin.testimonialStatusHidden',
  REJECTED: 'admin.testimonialStatusRejected',
}

/**
 * The platform's window onto submitted praise, and the first of its two
 * gates. Submitted text waits here before the owner sees it at all, because
 * an owner asked to hide abuse has already read it — so this page can pass
 * one to the owner or refuse it outright.
 *
 * What it still cannot do is publish. Whether a cleared testimonial appears
 * stays the owner's decision, which is what keeps this selected praise
 * rather than a review system; "pass to the owner" is therefore not an
 * approve button, and the hint under the heading says so.
 */
export function AdminTestimonialsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<Filter>('PENDING_REVIEW')
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  const testimonials = useQuery({
    queryKey: queryKeys.adminTestimonials(filter),
    queryFn: () => adminApi.testimonials(filter === 'ALL' ? undefined : filter),
    placeholderData: keepPreviousData,
  })

  const act = (messageKey: TranslationKey) => ({
    onSuccess: () => {
      toast.success(t(messageKey))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'testimonials'] })
    },
    onError: () => toast.error(t('admin.testimonialActionFailed')),
  })

  const clear = useMutation({
    mutationFn: (id: string) => adminApi.clearTestimonial(id),
    ...act('admin.testimonialCleared'),
  })

  const reject = useMutation({
    mutationFn: (id: string) => adminApi.rejectTestimonial(id),
    ...act('admin.testimonialRejected'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.removeTestimonial(id),
    onSuccess: () => {
      setConfirmingId(null)
      toast.success(t('admin.testimonialRemoved'))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'testimonials'] })
    },
    onError: () => toast.error(t('admin.testimonialRemoveFailed')),
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.testimonialsHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.testimonialsSubtitle')}</p>
        <p className="mt-1 text-sm text-ink-500">{t('admin.testimonialReviewHint')}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((option) => {
          const isActive = filter === option.value
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              aria-pressed={isActive}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
                isActive
                  ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                  : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
              )}
            >
              {t(option.labelKey)}
            </button>
          )
        })}
      </div>

      {testimonials.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : testimonials.isError ? (
        <ErrorState error={testimonials.error} onRetry={() => void testimonials.refetch()} />
      ) : testimonials.data && testimonials.data.length > 0 ? (
        <ul className="space-y-3">
          {testimonials.data.map((entry: AdminTestimonial) => (
            <li key={entry.id}>
              <Card>
                <CardBody className="space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink-900">{entry.author_name}</p>
                      <p className="mt-0.5 text-sm text-ink-500">
                        <Link
                          to={`/business/${encodeURIComponent(entry.business_slug)}`}
                          className="text-brand-700 hover:underline"
                        >
                          {entry.business_name}
                        </Link>
                        {' · '}
                        {formatDate(entry.created_at, locale)}
                      </p>
                    </div>
                    <Badge className={STATUS_STYLES[entry.status]}>
                      {t(STATUS_LABELS[entry.status])}
                    </Badge>
                  </div>

                  <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                    {entry.body}
                  </p>

                  <div className="flex flex-wrap items-center justify-end gap-2">
                    {/* Only while it is ours to act on. Once it is with the
                        owner, or they have acted, the platform's remaining
                        power is removal. */}
                    {entry.status === 'PENDING_REVIEW' ? (
                      <>
                        <Button
                          size="sm"
                          loading={clear.isPending}
                          onClick={() => clear.mutate(entry.id)}
                        >
                          <Check className="h-4 w-4" aria-hidden="true" />
                          {t('admin.testimonialClear')}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          loading={reject.isPending}
                          onClick={() => reject.mutate(entry.id)}
                        >
                          <X className="h-4 w-4" aria-hidden="true" />
                          {t('admin.testimonialReject')}
                        </Button>
                      </>
                    ) : null}
                    {confirmingId === entry.id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-ink-500">
                          {t('admin.testimonialRemoveConfirm')}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setConfirmingId(null)}
                          disabled={remove.isPending}
                        >
                          {t('admin.testimonialCancel')}
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          loading={remove.isPending}
                          onClick={() => remove.mutate(entry.id)}
                        >
                          {t('admin.testimonialRemove')}
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setConfirmingId(entry.id)}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        {t('admin.testimonialRemove')}
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('admin.testimonialsEmpty')} />
      )}
    </div>
  )
}
