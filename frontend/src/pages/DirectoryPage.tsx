import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { LocateFixed, SlidersHorizontal, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { ErrorState, NoSearchResults } from '@/components/ui/States'
import { BusinessCard } from '@/features/businesses/BusinessCard'
import { Pagination } from '@/features/businesses/Pagination'
import { PageBanner } from '@/components/layout/PageBanner'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { DisplacedFilterButton } from '@/features/directory/DisplacedFilterButton'
import { useNearestSort } from '@/features/directory/useNearestSort'
import { SearchBox } from '@/features/search/SearchBox'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { trackDirectoryView } from '@/services/analytics'
import { publicBusinessApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { BusinessSortOption } from '@/types/api'

const ALL = '__all__'
const SORT_KEYS: Record<BusinessSortOption, TranslationKey> = {
  newest: 'directory.sortNewest',
  nearest: 'directory.sortNearest',
  rating: 'directory.sortRating',
  name: 'directory.sortName',
  oldest: 'directory.sortOldest',
}

export function DirectoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const category = searchParams.get('category') ?? ''
  const location = searchParams.get('location') ?? ''
  const displaced = searchParams.get('displaced') === '1'
  const chosenSort = searchParams.get('sort') as BusinessSortOption | null
  const page = Number(searchParams.get('page') ?? '1')
  // The filters on screen, never the search text: see services/analytics.ts.
  useEffect(() => {
    trackDirectoryView({ directory: 'shops', category, location, displaced })
  }, [category, location, displaced])
  const setSort = useCallback(
    (value: BusinessSortOption) => {
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
  } = useNearestSort<BusinessSortOption>(chosenSort, setSort, 'rating')

  const [filtersOpen, setFiltersOpen] = useState(false)
  const t = useT()

  useSeo({
    title: q ? t('directory.seoSearchTitle', { query: q }) : t('directory.seoTitle'),
    description: t('directory.seoDescription'),
    canonicalPath: '/businesses',
  })

  const categories = useCategories()
  const { groups } = useLocationGroups()

  const results = useQuery({
    queryKey: queryKeys.businesses({ q, category, location, displaced, sort, lat: near?.lat, lng: near?.lng, page }),
    queryFn: () =>
      publicBusinessApi.search({
        q: q || undefined,
        category: category || undefined,
        location: location || undefined,
        displaced: displaced || undefined,
        sort,
        lat: near?.lat,
        lng: near?.lng,
        page,
        page_size: 24,
      }),
    placeholderData: keepPreviousData,
  })

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

  const hasFilters = Boolean(q || category || location || displaced) || chosenSort !== null
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <>
      <PageBanner
        page="products"
        title={t('directory.heading')}
        subtitle={
          results.data
            ? t('directory.resultCount', { count: results.data.meta.total })
            : t('directory.introFallback')
        }
      />
      <div className="container-page py-10">
        {/* The other two directories, one tap away. Without this each
            directory was an island: a search that came up empty here left
            the browser's back button as the only way across. */}
        <BrowseSwitcher current="businesses" />

        {/* The home page's box, suggesting as someone types; a plain search
            narrows this directory rather than leaving it. */}
        <div className="mb-4">
          <SearchBox
            appearance="page"
            value={q}
            label={t('directory.searchLabel')}
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

        <div className={`mb-6 grid gap-3 sm:grid-cols-3 ${filtersOpen ? 'grid' : 'hidden sm:grid'}`}>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-category">
              {t('directory.category')}
            </label>
            <Select
              value={category || ALL}
              onValueChange={(value) => updateParams({ category: value === ALL ? '' : value })}
            >
              <SelectTrigger aria-labelledby="filter-category">
                <SelectValue placeholder={t('directory.allCategories')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>{t('directory.allCategories')}</SelectItem>
                {/* The fullest categories first, each with its count. */}
                {[...(categories.data ?? [])]
                  .sort((a, b) => b.business_count - a.business_count)
                  .map((item) => (
                  <SelectItem key={item.id} value={item.slug}>
                    {t('directory.categoryWithCount', {
                      name: item.name_ar,
                      count: item.business_count,
                    })}
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
              countOf={(node) => node.business_count}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-sort">
              {t('directory.sort')}
            </label>
            <Select value={sort} onValueChange={(value) => chooseSort(value as BusinessSortOption)}>
              <SelectTrigger aria-labelledby="filter-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SORT_KEYS) as BusinessSortOption[]).map((option) => (
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
          ) : results.data && results.data.items.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {results.data.items.map((business) => (
                  <BusinessCard key={business.id} business={business} />
                ))}
              </div>
              <Pagination
                meta={results.data.meta}
                onChange={(nextPage) => updateParams({ page: String(nextPage) })}
              />
            </>
          ) : (
            <NoSearchResults onReset={hasFilters ? resetFilters : undefined} />
          )}
        </div>
      </div>
    </>
  )
}
