import { useQuery } from '@tanstack/react-query'
import { Briefcase, Building2, Search, SlidersHorizontal, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { JOB_TYPE_LABELS, JobCard, WORK_MODE_KEYS } from '@/features/jobs/JobCard'
import { JobLinksSidebar } from '@/features/jobs/JobLinksSidebar'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { jobApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { JobOpening, JobType, WorkMode } from '@/types/api'

const ALL = '__all__'
const TYPES: JobType[] = ['FULL_TIME', 'PART_TIME', 'INTERNSHIP', 'FREELANCE', 'REMOTE']
const MODES: WorkMode[] = ['ON_SITE', 'REMOTE', 'BOTH']

/**
 * Job openings the platform posts (29 Oct 2026), redesigned 31 Oct 2026:
 * open ones first, the newest first, then the closed ones under their own
 * heading, faded. There are at most sixty, so the filters narrow the list
 * already loaded rather than asking the server again.
 */
export function VacanciesPage() {
  const t = useT()
  useSeo({
    title: `${t('vacancies.title')} | ${t('app.name')}`,
    description: t('vacancies.subtitle'),
    canonicalPath: '/vacancies',
  })
  const jobs = useQuery({ queryKey: queryKeys.jobOpenings, queryFn: jobApi.list })
  const [params, setParams] = useSearchParams()
  const [filtersOpen, setFiltersOpen] = useState(false)
  const q = params.get('q') ?? ''
  const location = params.get('location') ?? ''
  const type = params.get('type') ?? ''
  const mode = params.get('mode') ?? ''

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }
  const hasFilters = Boolean(q || location || type || mode)

  const all = jobs.data ?? []
  const locations = useMemo(() => {
    const seen = new Map<string, string>()
    for (const job of all) if (job.location) seen.set(job.location.slug, job.location.name_ar)
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1], 'ar'))
  }, [all])

  const matches = (job: JobOpening) => {
    if (location && job.location?.slug !== location) return false
    if (type && job.job_type !== type) return false
    // "Both" is worked either way, so it matches either filter.
    if (mode && job.work_mode !== mode && !(job.work_mode === 'BOTH' && mode !== 'BOTH')) return false
    if (q) {
      const needle = q.trim().toLocaleLowerCase()
      const haystack = `${job.title} ${job.description}`.toLocaleLowerCase()
      if (!haystack.includes(needle)) return false
    }
    return true
  }
  const shown = all.filter(matches)
  const open = shown.filter((job) => job.status === 'ACTIVE')
  const closed = shown.filter((job) => job.status !== 'ACTIVE')
  const openTotal = all.filter((job) => job.status === 'ACTIVE').length

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <Briefcase className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('vacancies.title')}</h1>
        <p className="mt-2 max-w-2xl text-ink-500">{t('vacancies.subtitle')}</p>
        {jobs.data ? (
          <p className="mt-1 text-sm font-semibold text-brand-700">
            {t('vacancies.openCount', { count: openTotal })}
          </p>
        ) : null}
        <Link
          to="/vacancies/offer"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-800 px-4 py-2.5 font-semibold text-white hover:bg-brand-900"
        >
          <Building2 className="h-5 w-5" aria-hidden="true" />
          {t('onboarding.offerEmployerTitle')}
        </Link>
      </header>

      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start lg:gap-8">
        <div className="min-w-0">
          {all.length > 0 ? (
            <div className="mb-6">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search
                    className="pointer-events-none absolute start-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-400"
                    aria-hidden="true"
                  />
                  <Input
                    type="search"
                    value={q}
                    onChange={(event) => set('q', event.target.value)}
                    placeholder={t('vacancies.searchLabel')}
                    aria-label={t('vacancies.searchLabel')}
                    className="ps-10"
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  className="sm:hidden"
                  onClick={() => setFiltersOpen((value) => !value)}
                  aria-expanded={filtersOpen}
                >
                  <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                  {t('vacancies.filters')}
                </Button>
              </div>
              <div className={`mt-3 gap-3 sm:grid sm:grid-cols-3 ${filtersOpen ? 'grid' : 'hidden'}`}>
                <FilterSelect
                  label={t('directory.location')}
                  allLabel={t('directory.allLocations')}
                  value={location}
                  onChange={(value) => set('location', value)}
                  options={locations.map(([slug, name]) => [slug, name])}
                />
                <FilterSelect
                  label={t('admin.jobTypeLabel')}
                  allLabel={t('vacancies.allTypes')}
                  value={type}
                  onChange={(value) => set('type', value)}
                  options={TYPES.map((value) => [value, t(JOB_TYPE_LABELS[value])])}
                />
                <FilterSelect
                  label={t('admin.jobWorkModeLabel')}
                  allLabel={t('talent.workModeAll')}
                  value={mode}
                  onChange={(value) => set('mode', value)}
                  options={MODES.map((value) => [value, t(WORK_MODE_KEYS[value])])}
                />
              </div>
              {hasFilters ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => setParams(new URLSearchParams(), { replace: true })}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                  {t('states.clearFilters')}
                </Button>
              ) : null}
            </div>
          ) : null}

          {jobs.isLoading ? (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-72 rounded-2xl" />
              ))}
            </div>
          ) : jobs.isError ? (
            <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
          ) : (
            <>
              {open.length > 0 ? (
                <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                  {open.map((job) => (
                    <JobCard key={job.id} job={job} />
                  ))}
                </div>
              ) : hasFilters && shown.length > 0 ? null : (
                <EmptyState
                  icon={<Briefcase className="h-7 w-7" aria-hidden="true" />}
                  title={hasFilters ? t('vacancies.noMatches') : t('vacancies.empty')}
                  description={hasFilters ? undefined : t('vacancies.emptyInvite')}
                />
              )}
              {closed.length > 0 ? (
                <section className="mt-12" aria-labelledby="closed-heading">
                  <h2 id="closed-heading" className="mb-4 text-xl text-ink-700">
                    {t('vacancies.closedHeading')}
                  </h2>
                  <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                    {closed.map((job) => (
                      <JobCard key={job.id} job={job} />
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          )}
        </div>
        <JobLinksSidebar
          audience="seekers"
          className="mt-10 lg:sticky lg:top-24 lg:mt-0"
        />
      </div>
    </div>
  )
}

function FilterSelect({
  label,
  allLabel,
  value,
  onChange,
  options,
}: {
  label: string
  allLabel: string
  value: string
  onChange: (value: string) => void
  options: [string, string][]
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-ink-700">{label}</span>
      <Select value={value || ALL} onValueChange={(next) => onChange(next === ALL ? '' : next)}>
        <SelectTrigger aria-label={label}>
          <SelectValue placeholder={allLabel} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>{allLabel}</SelectItem>
          {options.map(([optionValue, optionLabel]) => (
            <SelectItem key={optionValue} value={optionValue}>
              {optionLabel}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  )
}
