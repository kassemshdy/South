import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  BadgeCheck,
  BriefcaseBusiness,
  FileText,
  House,
  LocateFixed,
  SearchX,
  SlidersHorizontal,
  UserPlus,
  X,
  Zap,
} from 'lucide-react'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { useNearestSort } from '@/features/directory/useNearestSort'
import { useAuth } from '@/features/auth/AuthContext'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { SearchBox } from '@/features/search/SearchBox'
import { CandidateBanner } from '@/features/talent/candidate/CandidateBanner'
import { CandidateCard } from '@/features/talent/candidate/CandidateCard'
import {
  EDUCATION_KEYS,
  EDUCATION_LEVELS,
  EXPERIENCE_BANDS,
  EXPERIENCE_KEYS,
  WORK_TYPE_KEYS,
  WORK_TYPES,
  educationFrom,
  experienceFrom,
  workTypeFrom,
} from '@/features/talent/candidate/labels'
import { useSeo } from '@/hooks/useSeo'
import { useLocationGroups, useTalentSkills } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { trackDirectoryView } from '@/services/analytics'
import { publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { TalentSortOption } from '@/types/api'
import { cn } from '@/utils/cn'

const ALL = '__all__'
const PAGE_SIZE = 12

type CandidateSort = Extract<TalentSortOption, 'best' | 'newest' | 'experience' | 'nearest'>

const SORTS: { value: CandidateSort; key: TranslationKey }[] = [
  { value: 'best', key: 'candidate.sortBest' },
  { value: 'newest', key: 'candidate.sortNewest' },
  { value: 'experience', key: 'candidate.sortExperience' },
  { value: 'nearest', key: 'candidate.sortNearest' },
]

function sortFrom(value: string | null): CandidateSort | null {
  return SORTS.find((sort) => sort.value === value)?.value ?? null
}

/** A filter chip that toggles one `?name=1` parameter. */
function Chip({
  active,
  onClick,
  icon,
  children,
  loading,
}: {
  active: boolean
  onClick: () => void
  icon: ReactNode
  children: ReactNode
  loading?: boolean
}) {
  return (
    <Button
      variant={active ? 'primary' : 'outline'}
      size="sm"
      aria-pressed={active}
      loading={loading}
      onClick={onClick}
    >
      {icon}
      {children}
    </Button>
  )
}

/**
 * The candidate directory at `/jobs` (the owners' ticket, 31 Oct 2026): the
 * same search and places as services, with what an employer filters on --
 * experience, education, the kind of work wanted, who can start now, who has
 * a CV and whose identity was checked.
 */
export function CandidateDirectory() {
  const t = useT()
  const { isAuthenticated } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const skill = searchParams.get('skill') ?? ''
  const location = searchParams.get('location') ?? ''
  const experience = experienceFrom(searchParams.get('experience'))
  const education = educationFrom(searchParams.get('education'))
  const workType = workTypeFrom(searchParams.get('work_type'))
  const availableNow = searchParams.get('available_now') === '1'
  const hasCv = searchParams.get('has_cv') === '1'
  const verified = searchParams.get('verified') === '1'
  const displaced = searchParams.get('displaced') === '1'
  const chosenSort = sortFrom(searchParams.get('sort'))
  const page = Number(searchParams.get('page') ?? '1')

  useEffect(() => {
    trackDirectoryView({ directory: 'job_seekers', skill, location, displaced })
  }, [skill, location, displaced])

  useSeo({
    title: q ? t('talent.seoSearchTitle', { query: q }) : t('talent.jobsSeoTitle'),
    description: t('talent.jobsSeoDescription'),
    canonicalPath: '/jobs',
  })

  const setSort = useCallback(
    (value: CandidateSort) => {
      const next = new URLSearchParams(searchParams)
      next.set('sort', value)
      next.delete('page')
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )
  const { sort, choose: chooseSort, locating, near } = useNearestSort<CandidateSort>(
    chosenSort,
    setSort,
    'best',
  )

  const [filtersOpen, setFiltersOpen] = useState(false)
  const skills = useTalentSkills()
  const { groups } = useLocationGroups()
  const jobCount = useCallback((row: { job_count: number }) => row.job_count, [])

  const query = {
    kind: 'JOB_SEEKER' as const,
    q: q || undefined,
    skill: skill || undefined,
    location: location || undefined,
    experience,
    education,
    work_type: workType,
    available_now: availableNow || undefined,
    has_cv: hasCv || undefined,
    verified: verified || undefined,
    displaced: displaced || undefined,
    sort,
    lat: near?.lat,
    lng: near?.lng,
    page,
    page_size: PAGE_SIZE,
  }
  const results = useQuery({
    queryKey: queryKeys.talents(query),
    queryFn: () => publicTalentApi.search(query),
    placeholderData: keepPreviousData,
  })

  const updateParams = useCallback(
    (changes: Record<string, string>) => {
      const next = new URLSearchParams(searchParams)
      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      if (!('page' in changes)) next.delete('page')
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )
  const toggle = (name: string, on: boolean) => updateParams({ [name]: on ? '' : '1' })

  const hasFilters =
    Boolean(
      q || skill || location || experience || education || workType || availableNow || hasCv,
    ) ||
    verified ||
    displaced ||
    chosenSort !== null
  const resetFilters = () => setSearchParams(new URLSearchParams())

  const selectFilter = (
    id: string,
    label: string,
    value: string | undefined,
    param: string,
    options: readonly { value: string; label: string }[],
  ) => (
    <div>
      <label className="mb-1.5 block text-sm font-semibold text-ink-700" id={id}>
        {label}
      </label>
      <Select
        value={value ?? ALL}
        onValueChange={(next) => updateParams({ [param]: next === ALL ? '' : next })}
      >
        <SelectTrigger aria-labelledby={id}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>{t('candidate.filterAny')}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )

  return (
    <>
      <CandidateBanner
        title={t('nav.jobs')}
        count={
          results.data
            ? t('talent.resultCount', { count: results.data.meta.total })
            : t('talent.introFallback')
        }
        line={t('candidate.heroLine')}
      />
      <div className="container-page py-8">
        <BrowseSwitcher current="jobs" />

        <div className="mb-4">
          <SearchBox
            appearance="page"
            value={q}
            label={t('talent.searchLabel')}
            onSearch={(value) => updateParams({ q: value })}
          >
            <Button
              type="button"
              variant="outline"
              className="h-12 shrink-0 sm:hidden"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
            >
              <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
              {t('candidate.filtersButton')}
            </Button>
          </SearchBox>
        </div>

        <div className={cn('mb-4 gap-3 sm:grid-cols-3 lg:grid-cols-6', filtersOpen ? 'grid' : 'hidden sm:grid')}>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-skill">
              {t('talent.skill')}
            </label>
            <Select
              value={skill || ALL}
              onValueChange={(value) => updateParams({ skill: value === ALL ? '' : value })}
            >
              <SelectTrigger aria-labelledby="filter-skill">
                <SelectValue placeholder={t('talent.allSkills')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>{t('talent.allSkills')}</SelectItem>
                {[...(skills.data ?? [])]
                  .sort((a, b) => b.job_count - a.job_count)
                  .map((item) => (
                    <SelectItem key={item.id} value={item.slug}>
                      {t('directory.categoryWithCount', { name: item.name_ar, count: item.job_count })}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" htmlFor="filter-location">
              {t('directory.location')}
            </label>
            <LocationCombobox
              id="filter-location"
              by="slug"
              emptyLabel={t('directory.allLocations')}
              value={location}
              onChange={(value) => updateParams({ location: value })}
              groups={groups}
              placeholder={t('directory.allLocations')}
              countOf={jobCount}
            />
          </div>

          {selectFilter(
            'filter-experience',
            t('candidate.filterExperience'),
            experience,
            'experience',
            EXPERIENCE_BANDS.map((band) => ({ value: band, label: t(EXPERIENCE_KEYS[band]) })),
          )}
          {selectFilter(
            'filter-education',
            t('candidate.filterEducation'),
            education,
            'education',
            EDUCATION_LEVELS.map((level) => ({ value: level, label: t(EDUCATION_KEYS[level]) })),
          )}
          {selectFilter(
            'filter-work-type',
            t('candidate.filterWorkType'),
            workType,
            'work_type',
            WORK_TYPES.map((type) => ({ value: type, label: t(WORK_TYPE_KEYS[type]) })),
          )}

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-sort">
              {t('directory.sort')}
            </label>
            <Select value={sort} onValueChange={(value) => chooseSort(value as CandidateSort)}>
              <SelectTrigger aria-labelledby="filter-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORTS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {t(option.key)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className={cn('mb-6 flex-wrap items-center gap-2', filtersOpen ? 'flex' : 'hidden sm:flex')}>
          <Chip
            active={availableNow}
            onClick={() => toggle('available_now', availableNow)}
            icon={<Zap className="h-4 w-4" aria-hidden="true" />}
          >
            {t('candidate.chipAvailableNow')}
          </Chip>
          <Chip
            active={hasCv}
            onClick={() => toggle('has_cv', hasCv)}
            icon={<FileText className="h-4 w-4" aria-hidden="true" />}
          >
            {t('candidate.chipHasCv')}
          </Chip>
          <Chip
            active={verified}
            onClick={() => toggle('verified', verified)}
            icon={<BadgeCheck className="h-4 w-4" aria-hidden="true" />}
          >
            {t('candidate.chipVerified')}
          </Chip>
          <Chip
            active={sort === 'nearest'}
            loading={locating}
            onClick={() => chooseSort('nearest')}
            icon={<LocateFixed className="h-4 w-4" aria-hidden="true" />}
          >
            {t('candidate.chipNearest')}
          </Chip>
          <Chip
            active={displaced}
            onClick={() => toggle('displaced', displaced)}
            icon={<House className="h-4 w-4" aria-hidden="true" />}
          >
            {t('candidate.chipDisplaced')}
          </Chip>
          {hasFilters ? (
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <X className="h-4 w-4" aria-hidden="true" />
              {t('states.clearFilters')}
            </Button>
          ) : null}
        </div>

        <div aria-live="polite" aria-busy={results.isFetching}>
          {results.isLoading ? (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <BusinessCardSkeleton key={index} />
              ))}
            </div>
          ) : results.isError ? (
            <ErrorState error={results.error} onRetry={() => void results.refetch()} />
          ) : results.data && results.data.items.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {results.data.items.map((talent) => (
                  <CandidateCard key={talent.id} talent={talent} />
                ))}
              </div>
              <Pagination
                meta={results.data.meta}
                onChange={(nextPage) => updateParams({ page: String(nextPage) })}
              />
            </>
          ) : (
            <EmptyState
              icon={<SearchX className="h-7 w-7" aria-hidden="true" />}
              title={t('candidate.emptyTitle')}
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  {hasFilters ? (
                    <Button variant="outline" onClick={resetFilters}>
                      {t('states.clearFilters')}
                    </Button>
                  ) : null}
                  <Button asChild variant="ghost">
                    <Link to="/vacancies/offer">
                      <BriefcaseBusiness className="h-4 w-4" aria-hidden="true" />
                      {t('candidate.postJob')}
                    </Link>
                  </Button>
                </div>
              }
            />
          )}
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 rounded-2xl border-2 border-brand-200 bg-brand-50 p-6 text-center sm:flex-row sm:text-start">
          <p className="text-lg font-bold text-ink-900">{t('candidate.joinTitle')}</p>
          <Button asChild>
            {/* The public application for a visitor; an owner adds the
                profile from their dashboard, as the jobs hub does. */}
            <Link
              to={
                isAuthenticated
                  ? '/dashboard/talent?kind=JOB_SEEKER'
                  : '/register/talent?kind=JOB_SEEKER'
              }
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              {t('candidate.joinButton')}
            </Link>
          </Button>
        </div>
      </div>
    </>
  )
}
