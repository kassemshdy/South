import { useQuery } from '@tanstack/react-query'
import { GraduationCap } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { WorkshopCard } from '@/features/workshops/WorkshopCard'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { workshopApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { TranslationKey } from '@/i18n'
import type { WorkshopMode } from '@/types/api'

/** The `?mode=` values the page understands, and the filter each one sets. */
const MODES: { param: string | null; mode?: WorkshopMode; label: TranslationKey }[] = [
  { param: null, label: 'workshops.filterAll' },
  { param: 'online', mode: 'ONLINE', label: 'workshops.online' },
  { param: 'in-person', mode: 'IN_PERSON', label: 'workshops.inPerson' },
]

/**
 * The platform's workshops: what is coming, then what has been, narrowed to
 * the online ones or the in-person ones by `?mode=`.
 */
export function WorkshopsPage() {
  const t = useT()
  const [params, setParams] = useSearchParams()
  const current = MODES.find((entry) => entry.param === params.get('mode')) ?? MODES[0]!
  const mode = current.mode
  useSeo({
    title: `${t('workshops.title')} | ${t('app.name')}`,
    description: t('workshops.subtitle'),
    canonicalPath: '/workshops',
  })
  const upcoming = useQuery({
    queryKey: queryKeys.workshops({ when: 'upcoming', mode }),
    queryFn: () => workshopApi.list({ when: 'upcoming', mode }),
  })
  const past = useQuery({
    queryKey: queryKeys.workshops({ when: 'past', mode }),
    queryFn: () => workshopApi.list({ when: 'past', mode, limit: 12 }),
  })

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <GraduationCap className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('workshops.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('workshops.subtitle')}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          {MODES.map((entry) => (
            <button
              key={entry.label}
              type="button"
              aria-pressed={entry === current}
              onClick={() =>
                setParams(entry.param ? { mode: entry.param } : {}, { replace: true })
              }
              className={
                entry === current
                  ? 'rounded-full bg-brand-800 px-4 py-2 text-sm font-semibold text-white'
                  : 'rounded-full border border-ink-100 bg-white px-4 py-2 text-sm font-semibold text-ink-700 hover:border-brand-300'
              }
            >
              {t(entry.label)}
            </button>
          ))}
        </div>
      </header>

      <section aria-labelledby="upcoming-heading">
        <h2 id="upcoming-heading" className="mb-4 text-xl">
          {mode === 'ONLINE' ? t('workshops.onlineTitle') : t('workshops.upcoming')}
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
