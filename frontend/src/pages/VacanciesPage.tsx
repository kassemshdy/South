import { useQuery } from '@tanstack/react-query'
import { Briefcase } from 'lucide-react'

import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { JobCard } from '@/features/jobs/JobCard'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { jobApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/** Job openings the platform posts, the newest first (29 Oct 2026). */
export function VacanciesPage() {
  const t = useT()
  useSeo({
    title: `${t('vacancies.title')} | ${t('app.name')}`,
    description: t('vacancies.subtitle'),
    canonicalPath: '/vacancies',
  })
  const jobs = useQuery({ queryKey: queryKeys.jobOpenings, queryFn: jobApi.list })

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <Briefcase className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('vacancies.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('vacancies.subtitle')}</p>
      </header>
      {jobs.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-40 rounded-2xl" />
          ))}
        </div>
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
      ) : (jobs.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Briefcase className="h-7 w-7" aria-hidden="true" />}
          title={t('vacancies.empty')}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.data?.map((job) => <JobCard key={job.id} job={job} />)}
        </div>
      )}
    </div>
  )
}
