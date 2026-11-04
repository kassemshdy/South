import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query'
import { BadgeCheck, LayoutGrid, LocateFixed, SearchX, SlidersHorizontal, Star, X } from 'lucide-react'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { CategoryIcon } from '@/features/home/categoryIcon'
import { TalentCard } from '@/features/talent/TalentCard'
import { CandidateDirectory } from '@/features/talent/candidate/CandidateDirectory'
import { WORK_MODE_KEYS } from '@/features/talent/labels'
import { useLocationGroups, useTalentSkills } from '@/hooks/useTaxonomy'
import { PageBanner } from '@/components/layout/PageBanner'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { DisplacedFilterButton } from '@/features/directory/DisplacedFilterButton'
import { useNearestSort } from '@/features/directory/useNearestSort'
import { SearchBox } from '@/features/search/SearchBox'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { trackDirectoryView } from '@/services/analytics'
import { publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCoverKey, TalentKind, TalentQuery, TalentSortOption } from '@/types/api'

const ALL = '__all__'

type WorkModeFilter = NonNullable<TalentQuery['work_mode']>

/** What a visitor filters on; a profile that does both matches either. */
const WORK_MODE_FILTERS: WorkModeFilter[] = ['ON_SITE', 'REMOTE']

function workModeFrom(value: string | null): WorkModeFilter | undefined {
  return WORK_MODE_FILTERS.find((mode) => mode === value)
}

const SORT_KEYS: Record<TalentSortOption, TranslationKey> = {
  newest: 'directory.sortNewest',
  // Services: rated, ID on file, priced and filled-in providers first (the
  // services redesign, 3 Nov 2026). Newest stays the default.
  best: 'candidate.sortBest',
  nearest: 'directory.sortNearest',
  experience: 'talent.sortExperience',
  // Services only: a job application takes no testimonials.
  rating: 'directory.sortRating',
  name: 'talent.sortName',
  oldest: 'directory.sortOldest',
}

/**
 * The two halves of what was one talent directory, each its own page: the
 * same search, filters and cards, narrowed to one kind of profile.
 */
const KIND_PAGES: Record<
  TalentKind,
  {
    path: string
    titleKey: TranslationKey
    seoTitleKey: TranslationKey
    seoDescriptionKey: TranslationKey
    cover: PageCoverKey
    browseKey: 'services' | 'jobs'
  }
> = {
  SERVICE: {
    path: '/services',
    titleKey: 'nav.services',
    seoTitleKey: 'talent.servicesSeoTitle',
    seoDescriptionKey: 'talent.seoDescription',
    cover: 'talent',
    browseKey: 'services',
  },
  JOB_SEEKER: {
    path: '/jobs',
    titleKey: 'nav.jobs',
    seoTitleKey: 'talent.jobsSeoTitle',
    seoDescriptionKey: 'talent.jobsSeoDescription',
    cover: 'jobs',
    browseKey: 'jobs',
  },
}

/** `/talent`, from before the split: forwarded to services, filters kept. */
export function LegacyTalentRedirect() {
  const { search } = useLocation()
  return <Navigate to={`/services${search}`} replace />
}

/**
 * Job seekers have their own directory (the owners' ticket, 31 Oct 2026);
 * services keep this one. Two components rather than a branch inside one, so
 * moving between /services and /jobs remounts instead of reusing hooks.
 */
export function TalentDirectoryPage({ kind }: { kind: TalentKind }) {
  return kind === 'JOB_SEEKER' ? <CandidateDirectory /> : <TalentDirectory kind={kind} />
}

function TalentDirectory({ kind }: { kind: TalentKind }) {
  const page_ = KIND_PAGES[kind]
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const skill = searchParams.get('skill') ?? ''
  const location = searchParams.get('location') ?? ''
  const displaced = searchParams.get('displaced') === '1'
  // Services only: a job application is not asked how it is delivered.
  const workMode = kind === 'SERVICE' ? workModeFrom(searchParams.get('work_mode')) : undefined
  const chosenSort = searchParams.get('sort') as TalentSortOption | null
  // Only providers with an ID on file (the services redesign, 3 Nov 2026).
  const verified = kind === 'SERVICE' && searchParams.get('verified') === '1'
  // The filters on screen, never the search text: see services/analytics.ts.
  useEffect(() => {
    trackDirectoryView({ directory: kind === 'JOB_SEEKER' ? 'job_seekers' : 'services', skill, location, displaced })
  }, [skill, location, displaced, kind])
  const setSort = useCallback(
    (value: TalentSortOption) => {
      const next = new URLSearchParams(searchParams)
      next.set('sort', value)
      next.delete('page')
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )
  const {
    sort,
    choose: chooseSort,
    locating,
    near,
  } = useNearestSort<TalentSortOption>(
    chosenSort,
    setSort,
    // Newest first on both pages (the owners' decision, 30 Oct 2026).
    'newest',
  )

  const [filtersOpen, setFiltersOpen] = useState(false)
  const t = useT()

  useSeo({
    title: q ? t('talent.seoSearchTitle', { query: q }) : t(page_.seoTitleKey),
    description: t(page_.seoDescriptionKey),
    canonicalPath: page_.path,
  })

  const skills = useTalentSkills()
  // Services and job seekers share the skills and the places; each page
  // counts only its own kind.
  const countOfKind = useCallback(
    (row: { service_count: number; job_count: number }) =>
      kind === 'SERVICE' ? row.service_count : row.job_count,
    [kind],
  )
  const { groups } = useLocationGroups()
  const categoryTiles = [...(skills.data ?? [])]
    .filter((item) => countOfKind(item) > 0)
    .sort((a, b) => countOfKind(b) - countOfKind(a))

  // "Show more" rather than numbered pages (the services redesign): each
  // press appends the next 24 to the grid.
  const results = useInfiniteQuery({
    queryKey: [
      ...queryKeys.talents({
      q,
      skill,
      location,
      sort,
      lat: near?.lat,
      lng: near?.lng,
      kind,
      work_mode: workMode,
      displaced,
        verified,
      }),
      'more',
    ],
    queryFn: ({ pageParam }) =>
      publicTalentApi.search({
        kind,
        q: q || undefined,
        skill: skill || undefined,
        location: location || undefined,
        work_mode: workMode,
        displaced: displaced || undefined,
        verified: verified || undefined,
        sort,
        lat: near?.lat,
        lng: near?.lng,
        page: pageParam,
        page_size: 24,
      }),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.meta.page < last.meta.total_pages ? last.meta.page + 1 : undefined,
    placeholderData: keepPreviousData,
  })
  const talents = results.data?.pages.flatMap((page) => page.items) ?? []
  const total = results.data?.pages[0]?.meta.total ?? 0

  const updateParams = useCallback(
    (changes: Record<string, string>) => {
      const next = new URLSearchParams(searchParams)
      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      // Any filter change returns to the first page; staying on page 5 of a new
      // result set is almost always wrong.
      if (!('page' in changes)) next.delete('page')
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )

  const hasFilters =
    Boolean(q || skill || location || workMode || displaced || verified) || chosenSort !== null
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <>
      <PageBanner
        page={page_.cover}
        title={t(page_.titleKey)}
        subtitle={
          results.data
            ? t(kind === 'SERVICE' ? 'talent.providerCount' : 'talent.resultCount', {
                count: total,
              })
            : t('talent.introFallback')
        }
      />
      <div className="container-page py-10">
        {/* The other two directories, one tap away. Without this each
            directory was an island: a search that came up empty here left
            the browser's back button as the only way across. */}
        <BrowseSwitcher current={page_.browseKey} />

        {/* Most visitors browse by category before they search (the owners'
            services redesign, 31 Oct 2026): the skills with providers in
            them, the fullest first, one tap to narrow the list. */}
        {kind === 'SERVICE' && categoryTiles.length > 0 ? (
          <nav aria-label={t('talent.categoriesLabel')} className="-mx-4 mb-6 overflow-x-auto px-4">
            <ul className="flex gap-3">
              <li className="shrink-0">
                <CategoryTile
                  active={!skill}
                  label={t('talent.allSkills')}
                  icon={<LayoutGrid className="h-6 w-6" aria-hidden="true" />}
                  onClick={() => updateParams({ skill: '' })}
                />
              </li>
              {categoryTiles.map((item) => (
                <li key={item.id} className="shrink-0">
                  <CategoryTile
                    active={skill === item.slug}
                    label={item.name_ar}
                    icon={<CategoryIcon name={item.icon} className="h-6 w-6" />}
                    onClick={() => updateParams({ skill: skill === item.slug ? '' : item.slug })}
                  />
                </li>
              ))}
            </ul>
          </nav>
        ) : null}

        {/* The home page's box, suggesting as someone types; a plain search
            narrows this directory rather than leaving it. */}
        <div className="mb-4">
          <SearchBox
            appearance="page"
            value={q}
            label={t('talent.searchLabel')}
            onSearch={(query) => updateParams({ q: query })}
          >
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-12 w-12 shrink-0 sm:hidden"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
              aria-label={t('directory.filtersAria')}
            >
              <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
            </Button>
          </SearchBox>
        </div>

        <div
          className={`mb-6 grid gap-3 ${kind === 'SERVICE' ? 'sm:grid-cols-2 lg:grid-cols-4' : 'sm:grid-cols-3'} ${filtersOpen ? 'grid' : 'hidden sm:grid'}`}
        >
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
                {/* This directory's own count, the fullest skills first. */}
                {[...(skills.data ?? [])]
                  .sort((a, b) => countOfKind(b) - countOfKind(a))
                  .map((item) => (
                  <SelectItem key={item.id} value={item.slug}>
                    {t('directory.categoryWithCount', { name: item.name_ar, count: countOfKind(item) })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" htmlFor="filter-location">
              {t('directory.location')}
            </label>
            {/* Typed into, like the sellers' own picker, rather than scrolled. */}
            <LocationCombobox
              id="filter-location"
              by="slug"
              emptyLabel={t('directory.allLocations')}
              value={location}
              onChange={(value) => updateParams({ location: value })}
              groups={groups}
              placeholder={t('directory.allLocations')}
              countOf={countOfKind}
            />
          </div>

          {kind === 'SERVICE' ? (
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-work-mode">
                {t('talent.workModeLabel')}
              </label>
              <Select
                value={workMode ?? ALL}
                onValueChange={(value) => updateParams({ work_mode: value === ALL ? '' : value })}
              >
                <SelectTrigger aria-labelledby="filter-work-mode">
                  <SelectValue placeholder={t('talent.workModeAll')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>{t('talent.workModeAll')}</SelectItem>
                  {WORK_MODE_FILTERS.map((mode) => (
                    <SelectItem key={mode} value={mode}>
                      {t(WORK_MODE_KEYS[mode])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-sort">
              {t('directory.sort')}
            </label>
            <Select value={sort} onValueChange={(value) => chooseSort(value as TalentSortOption)}>
              <SelectTrigger aria-labelledby="filter-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SORT_KEYS) as TalentSortOption[])
                  .filter((option) => option !== 'rating' || kind === 'SERVICE')
                  .filter((option) => option !== 'best' || kind === 'SERVICE')
                  .map((option) => (
                    <SelectItem key={option} value={option}>
                      {t(SORT_KEYS[option])}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="mb-6 flex flex-wrap items-center gap-2">
          {/* A button as well as an entry in the sort list, as the owners
              asked: it is the one order a visitor would not think to look for. */}
          <Button
            variant={sort === 'nearest' ? 'primary' : 'outline'}
            size="sm"
            aria-pressed={sort === 'nearest'}
            loading={locating}
            onClick={() => chooseSort('nearest')}
          >
            <LocateFixed className="h-4 w-4" aria-hidden="true" />
            {t('directory.sortNearest')}
          </Button>
          {kind === 'SERVICE' ? (
            <Button
              variant={sort === 'rating' ? 'primary' : 'outline'}
              size="sm"
              aria-pressed={sort === 'rating'}
              onClick={() => chooseSort(sort === 'rating' ? 'newest' : 'rating')}
            >
              <Star className="h-4 w-4" aria-hidden="true" />
              {t('directory.sortRating')}
            </Button>
          ) : null}
          {kind === 'SERVICE' ? (
            <Button
              variant={verified ? 'primary' : 'outline'}
              size="sm"
              aria-pressed={verified}
              onClick={() => updateParams({ verified: verified ? '' : '1' })}
            >
              <BadgeCheck className="h-4 w-4" aria-hidden="true" />
              {t('talent.verifiedOnly')}
            </Button>
          ) : null}
          <DisplacedFilterButton
            active={displaced}
            onToggle={() => updateParams({ displaced: displaced ? '' : '1' })}
          />
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
          ) : talents.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {talents.map((talent) => (
                  <TalentCard key={talent.id} talent={talent} />
                ))}
              </div>
              {results.hasNextPage ? (
                <div className="mt-8 flex justify-center">
                  <Button
                    variant="outline"
                    size="lg"
                    loading={results.isFetchingNextPage}
                    onClick={() => void results.fetchNextPage()}
                  >
                    {t('talent.showMore', { count: total - talents.length })}
                  </Button>
                </div>
              ) : null}
            </>
          ) : (
            <EmptyState
              icon={<SearchX className="h-7 w-7" aria-hidden="true" />}
              title={t(kind === 'SERVICE' ? 'talent.noProvidersTitle' : 'states.noResultsTitle')}
              description={t('states.noResultsDescription')}
              action={
                hasFilters ? (
                  <Button variant="outline" onClick={resetFilters}>
                    {t('states.clearFilters')}
                  </Button>
                ) : null
              }
            />
          )}
        </div>

        {/* The way in for someone with a service of their own, where a
            visitor who has scrolled the whole list ends up. */}
        {kind === 'SERVICE' ? (
          <aside className="mt-10 flex flex-col items-center gap-4 rounded-2xl bg-brand-800 px-6 py-8 text-center text-white sm:flex-row sm:justify-between sm:text-start">
            <p className="text-lg font-bold">{t('talent.signupBannerTitle')}</p>
            <Button asChild variant="secondary">
              <Link to="/register/talent?kind=SERVICE">{t('talent.signupBannerCta')}</Link>
            </Button>
          </aside>
        ) : null}
      </div>
    </>
  )
}

function CategoryTile({
  active,
  label,
  icon,
  onClick,
}: {
  active: boolean
  label: string
  icon: ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex h-24 w-28 flex-col items-center justify-center gap-2 rounded-2xl border px-2 text-center text-sm font-semibold transition-colors ${
        active
          ? 'border-brand-700 bg-brand-700 text-white'
          : 'border-ink-100 bg-white text-ink-800 hover:border-brand-300 hover:bg-sand-50'
      }`}
    >
      {icon}
      <span className="line-clamp-2 leading-tight">{label}</span>
    </button>
  )
}
