import { useQuery } from '@tanstack/react-query'
import { GraduationCap } from 'lucide-react'

import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { WorkshopCard } from '@/features/workshops/WorkshopCard'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { workshopApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/** The platform's workshops: what is coming, then what has been. */
export function WorkshopsPage() {
  const t = useT()
  useSeo({
    title: `${t('workshops.title')} | ${t('app.name')}`,
    description: t('workshops.subtitle'),
    canonicalPath: '/workshops',
  })
  const upcoming = useQuery({
    queryKey: queryKeys.workshops({ when: 'upcoming' }),
    queryFn: () => workshopApi.list({ when: 'upcoming' }),
  })
  const past = useQuery({
    queryKey: queryKeys.workshops({ when: 'past' }),
    queryFn: () => workshopApi.list({ when: 'past', limit: 12 }),
  })

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <GraduationCap className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('workshops.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('workshops.subtitle')}</p>
      </header>

      <section aria-labelledby="upcoming-heading">
        <h2 id="upcoming-heading" className="mb-4 text-xl">
          {t('workshops.upcoming')}
        </h2>
        {upcoming.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-72 rounded-2xl" />
            ))}
          </div>
        ) : upcoming.isError ? (
          <ErrorState error={upcoming.error} onRetry={() => void upcoming.refetch()} />
        ) : (upcoming.data ?? []).length === 0 ? (
          <EmptyState
            icon={<GraduationCap className="h-7 w-7" aria-hidden="true" />}
            title={t('workshops.empty')}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {upcoming.data?.map((workshop) => (
              <WorkshopCard key={workshop.id} workshop={workshop} />
            ))}
          </div>
        )}
      </section>

      {(past.data ?? []).length > 0 ? (
        <section aria-labelledby="past-heading" className="mt-12">
          <h2 id="past-heading" className="mb-4 text-xl">
            {t('workshops.past')}
          </h2>
          <div className="grid gap-4 opacity-80 sm:grid-cols-2 lg:grid-cols-3">
            {past.data?.map((workshop) => (
              <WorkshopCard key={workshop.id} workshop={workshop} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
