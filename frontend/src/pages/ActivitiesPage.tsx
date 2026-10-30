import { useQuery } from '@tanstack/react-query'
import { CalendarDays, Megaphone } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { activityApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

/**
 * Every kept development activity, the same ones the home page's carousel
 * turns through, as the menu's own page (the owners' ticket, 29 Oct 2026).
 */
export function ActivitiesPage() {
  const { t, locale } = useI18n()
  useSeo({
    title: `${t('activities.title')} | ${t('app.name')}`,
    description: t('activities.subtitle'),
    canonicalPath: '/activities',
  })
  const activities = useQuery({ queryKey: queryKeys.activities, queryFn: activityApi.list })

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <Megaphone className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('activities.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('activities.subtitle')}</p>
      </header>

      {activities.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-72 rounded-2xl" />
          ))}
        </div>
      ) : activities.isError ? (
        <ErrorState error={activities.error} onRetry={() => void activities.refetch()} />
      ) : (activities.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Megaphone className="h-7 w-7" aria-hidden="true" />}
          title={t('activities.empty')}
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activities.data?.map((activity) => (
            <li key={activity.id} className="min-w-0">
              <Link
                to={`/activities/${encodeURIComponent(activity.slug)}`}
                className="block h-full overflow-hidden rounded-2xl bg-white shadow-card transition-shadow hover:shadow-lift"
              >
                {activity.image_url ? (
                  <img
                    src={activity.image_url}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    className="aspect-[16/9] w-full object-cover"
                  />
                ) : null}
                <div className="p-4">
                  {activity.starts_at ? (
                    <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-clay-700">
                      <CalendarDays className="h-4 w-4" aria-hidden="true" />
                      {formatDate(activity.starts_at, locale)}
                    </p>
                  ) : null}
                  <h2 className="line-clamp-2 text-lg font-bold text-ink-900" dir="auto">
                    {activity.title}
                  </h2>
                  {activity.summary ? (
                    <p className="mt-1 line-clamp-2 text-sm text-ink-500" dir="auto">
                      {activity.summary}
                    </p>
                  ) : null}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
