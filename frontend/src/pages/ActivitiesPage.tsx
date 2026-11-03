import { useInfiniteQuery } from '@tanstack/react-query'
import { Megaphone } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { ActivitiesCarousel } from '@/features/activities/ActivitiesCarousel'
import { hasEnded, KIND_KEYS } from '@/features/activities/labels'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { activityApi } from '@/services/api/endpoints'
import type { Activity } from '@/types/api'
import { formatDate } from '@/utils/format'

const PAGE_SIZE = 10
const LATEST_COUNT = 6

/**
 * The activities page as a news page (the owners' ticket, 31 Oct 2026,
 * modelled on a news site's layout in Janoubona's own colours): the shared
 * carousel, then the announcements as rows -- upcoming first, the order the
 * API returns -- ten at a time, and a side column with the latest titles and
 * image tiles. One column on a phone: carousel, list, side column.
 */
export function ActivitiesPage() {
  const { t } = useI18n()
  useSeo({
    title: `${t('activities.title')} | ${t('app.name')}`,
    description: t('activities.subtitle'),
    canonicalPath: '/activities',
  })
  const pages = useInfiniteQuery({
    queryKey: ['activities', 'page'],
    queryFn: ({ pageParam }) => activityApi.list({ limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last, all) =>
      last.length < PAGE_SIZE ? undefined : all.length * PAGE_SIZE,
  })
  const items = pages.data?.pages.flat() ?? []
  // The side column reads the same first page: the API has no separate
  // "most recently added" order for visitors, so "latest" is the head of
  // the list as it is shown.
  const latest = (pages.data?.pages[0] ?? []).slice(0, LATEST_COUNT)
  const tiles = (pages.data?.pages[0] ?? []).slice(0, 4)

  return (
    <div className="container-page py-10">
      <header className="mb-6">
        <Megaphone className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('activities.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('activities.subtitle')}</p>
      </header>

      {pages.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="aspect-[16/9] w-full rounded-2xl sm:aspect-[16/6]" />
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-32 rounded-2xl" />
          ))}
        </div>
      ) : pages.isError ? (
        <ErrorState error={pages.error} onRetry={() => void pages.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Megaphone className="h-7 w-7" aria-hidden="true" />}
          title={t('activities.empty')}
        />
      ) : (
        <>
          <ActivitiesCarousel heading={false} />
          <div className="mt-8 grid gap-8 lg:grid-cols-3">
            <section className="min-w-0 lg:col-span-2">
              <ul className="divide-y divide-ink-100">
                {items.map((activity) => (
                  <li key={activity.id}>
                    <ActivityRow activity={activity} />
                  </li>
                ))}
              </ul>
              {pages.hasNextPage ? (
                <div className="mt-6 flex justify-center">
                  <Button
                    type="button"
                    variant="outline"
                    loading={pages.isFetchingNextPage}
                    onClick={() => void pages.fetchNextPage()}
                  >
                    {t('activitiesPage.loadMore')}
                  </Button>
                </div>
              ) : null}
            </section>

            <aside className="min-w-0 space-y-6">
              <div className="rounded-2xl bg-sand-100 p-5">
                <h2 className="text-lg font-bold text-ink-900">{t('activitiesPage.latest')}</h2>
                <ul className="mt-3 space-y-2">
                  {latest.map((activity) => (
                    <li key={activity.id} className="min-w-0">
                      <Link
                        to={`/activities/${encodeURIComponent(activity.slug)}`}
                        className="block truncate text-ink-700 hover:text-brand-700 hover:underline"
                        dir="auto"
                      >
                        {activity.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <ul className="grid grid-cols-2 gap-3">
                {tiles.map((activity) => (
                  <li key={activity.id} className="min-w-0">
                    <Link
                      to={`/activities/${encodeURIComponent(activity.slug)}`}
                      className="group block overflow-hidden rounded-xl bg-white shadow-card"
                    >
                      {activity.image_url ? (
                        <img
                          src={activity.image_thumb_url ?? activity.image_url}
                          alt=""
                          loading="lazy"
                          decoding="async"
                          className="aspect-[4/3] w-full object-cover transition-transform group-hover:scale-105"
                        />
                      ) : null}
                      <p
                        className="line-clamp-2 bg-brand-800 px-2.5 py-2 text-sm font-semibold text-white"
                        dir="auto"
                      >
                        {activity.title}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        </>
      )}
    </div>
  )
}

/** One announcement: thumbnail at the start, bold title, then date · type. */
function ActivityRow({ activity }: { activity: Activity }) {
  const { t, locale } = useI18n()
  const ended = hasEnded(activity)
  const meta = [
    activity.starts_at ? formatDate(activity.starts_at, locale) : null,
    t(KIND_KEYS[activity.kind]),
  ].filter(Boolean)
  return (
    <Link
      to={`/activities/${encodeURIComponent(activity.slug)}`}
      className="group flex flex-col gap-4 py-5 sm:flex-row sm:items-start"
    >
      {activity.image_url ? (
        <div className="relative shrink-0 overflow-hidden rounded-xl sm:w-[360px]">
          <img
            src={activity.image_thumb_url ?? activity.image_url}
            alt=""
            loading="lazy"
            decoding="async"
            className="aspect-[9/5] w-full object-cover transition-transform group-hover:scale-105"
          />
          {ended ? (
            <span className="absolute start-2 top-2 rounded-full bg-ink-900/80 px-2.5 py-1 text-xs font-semibold text-white">
              {t('activitiesPage.ended')}
            </span>
          ) : null}
        </div>
      ) : null}
      <div className="min-w-0 flex-1">
        <h2
          className="line-clamp-3 text-lg font-bold leading-snug text-ink-900 group-hover:text-brand-700 sm:text-xl"
          dir="auto"
        >
          {activity.title}
        </h2>
        <p className="mt-2 text-sm font-semibold text-brand-700">{meta.join(' · ')}</p>
        {activity.summary ? (
          <p className="mt-2 line-clamp-2 text-sm text-ink-500" dir="auto">
            {activity.summary}
          </p>
        ) : null}
      </div>
    </Link>
  )
}
