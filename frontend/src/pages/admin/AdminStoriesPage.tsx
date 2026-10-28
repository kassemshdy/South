import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { StoryStatus } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDateTime } from '@/utils/format'

const FILTERS: { value: StoryStatus; labelKey: TranslationKey }[] = [
  { value: 'PENDING_REVIEW', labelKey: 'stories.statusPending' },
  { value: 'APPROVED', labelKey: 'stories.statusShowing' },
  { value: 'REJECTED', labelKey: 'stories.statusRejected' },
]

/**
 * Owners' photo stories waiting for review. Approving shows a story on the
 * home page for a day from that moment; rejecting keeps it off and tells
 * its owner so in their dashboard. Showing stories can be taken down here.
 */
export function AdminStoriesPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canModerate = useStaffCan('moderate')
  const [filter, setFilter] = useState<StoryStatus>('PENDING_REVIEW')
  const stories = useQuery({
    queryKey: queryKeys.adminStories(filter),
    queryFn: () => adminApi.stories(filter),
    placeholderData: keepPreviousData,
  })

  const done = (messageKey: TranslationKey) => ({
    onSuccess: () => {
      toast.success(t(messageKey))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'stories'] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.homeStories })
    },
    onError: (error: unknown) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })
  const approve = useMutation({ mutationFn: adminApi.approveStory, ...done('stories.approved') })
  const reject = useMutation({ mutationFn: adminApi.rejectStory, ...done('stories.rejected') })
  const remove = useMutation({ mutationFn: adminApi.deleteStory, ...done('stories.deleted') })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.storiesTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.storiesHint')}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={filter === option.value}
            onClick={() => setFilter(option.value)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
              filter === option.value
                ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
            )}
          >
            {t(option.labelKey)}
          </button>
        ))}
      </div>

      {stories.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : stories.isError ? (
        <ErrorState error={stories.error} onRetry={() => void stories.refetch()} />
      ) : (stories.data ?? []).length === 0 ? (
        <EmptyState title={t('admin.storiesEmpty')} />
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
          {(stories.data ?? []).map((story) => (
            <li key={story.id} className="overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card">
              <a href={story.image_url} target="_blank" rel="noopener noreferrer" className="block">
                <img
                  src={story.image_url}
                  alt={story.caption ?? story.listing_name}
                  className="aspect-[9/16] w-full bg-ink-900 object-cover"
                />
              </a>
              <div className="space-y-2 p-3 text-sm">
                <Link
                  to={`/admin/${story.listing_kind === 'business' ? 'businesses' : 'talent'}/${story.listing_id}`}
                  dir="auto"
                  className="block truncate font-bold text-brand-700 hover:underline"
                >
                  {story.listing_name}
                </Link>
                {story.caption ? (
                  <p dir="auto" className="line-clamp-3 text-ink-700">
                    {story.caption}
                  </p>
                ) : null}
                <p className="text-xs text-ink-500">
                  {story.status === 'APPROVED' && story.expires_at
                    ? t('stories.until', { time: formatDateTime(story.expires_at, locale) })
                    : formatDateTime(story.created_at, locale)}
                </p>
                {canModerate ? (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {story.status !== 'APPROVED' ? (
                      <Button
                        size="sm"
                        loading={approve.isPending && approve.variables === story.id}
                        onClick={() => approve.mutate(story.id)}
                      >
                        <Check className="h-4 w-4" aria-hidden="true" />
                        {t('stories.approve')}
                      </Button>
                    ) : null}
                    {story.status === 'PENDING_REVIEW' ? (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={reject.isPending && reject.variables === story.id}
                        onClick={() => reject.mutate(story.id)}
                      >
                        <X className="h-4 w-4" aria-hidden="true" />
                        {t('stories.reject')}
                      </Button>
                    ) : null}
                    {story.status !== 'PENDING_REVIEW' ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={remove.isPending && remove.variables === story.id}
                        onClick={() => {
                          if (window.confirm(t('stories.deleteConfirm'))) remove.mutate(story.id)
                        }}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        {t('common.delete')}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
