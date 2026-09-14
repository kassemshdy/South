import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Search, SlidersHorizontal, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { ErrorState, NoSearchResults } from '@/components/ui/States'
import { BusinessCard } from '@/features/businesses/BusinessCard'
import { Pagination } from '@/features/businesses/Pagination'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { publicBusinessApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { SortOption } from '@/types/api'

const ALL = '__all__'
const SORT_KEYS: Record<SortOption, TranslationKey> = {
  newest: 'directory.sortNewest',
  name: 'directory.sortName',
  oldest: 'directory.sortOldest',
}

export function DirectoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const category = searchParams.get('category') ?? ''
  const location = searchParams.get('location') ?? ''
  const sort = (searchParams.get('sort') as SortOption | null) ?? 'newest'
  const page = Number(searchParams.get('page') ?? '1')

  // Local mirror so typing feels instant; the URL updates on submit, which
  // keeps searches shareable and back/forward working.
  const [searchInput, setSearchInput] = useState(q)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const t = useT()

  useEffect(() => setSearchInput(q), [q])

  useSeo({
    title: q ? t('directory.seoSearchTitle', { query: q }) : t('directory.seoTitle'),
    description: t('directory.seoDescription'),
    canonicalPath: '/businesses',
  })

  const categories = useCategories()
  const { groups } = useLocationGroups()

  const results = useQuery({
    queryKey: queryKeys.businesses({ q, category, location, sort, page }),
    queryFn: () =>
      publicBusinessApi.search({
        q: q || undefined,
        category: category || undefined,
        location: location || undefined,
        sort,
        page,
        page_size: 12,
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

  const hasFilters = Boolean(q || category || location) || sort !== 'newest'
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="text-3xl">{t('directory.heading')}</h1>
        <p className="mt-2 text-ink-500">
          {results.data
            ? t('directory.resultCount', { count: results.data.meta.total })
            : t('directory.introFallback')}
        </p>
      </header>

      {/* The other two directories, one tap away. Without this each
          directory was an island: a search that came up empty here left
          the browser's back button as the only way across. */}
      <BrowseSwitcher current="businesses" />

      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          updateParams({ q: searchInput.trim() })
        }}
        className="mb-4 flex gap-2"
      >
        <label htmlFor="directory-search" className="sr-only">
          {t('directory.searchLabel')}
        </label>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute inset-y-0 start-4 my-auto h-5 w-5 text-ink-300" aria-hidden="true" />
          <input
            id="directory-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t('home.searchPlaceholder')}
            className="h-12 w-full rounded-xl border-2 border-ink-100 bg-white ps-12 pe-4 text-[15px] placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        <Button type="submit">{t('common.search')}</Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="sm:hidden"
          onClick={() => setFiltersOpen((open) => !open)}
          aria-expanded={filtersOpen}
          aria-label={t('directory.filtersAria')}
        >
          <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
        </Button>
      </form>

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
              {categories.data?.map((item) => (
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
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-location">
            {t('directory.location')}
          </label>
          <Select
            value={location || ALL}
            onValueChange={(value) => updateParams({ location: value === ALL ? '' : value })}
          >
            <SelectTrigger aria-labelledby="filter-location">
              <SelectValue placeholder={t('directory.allLocations')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t('directory.allLocations')}</SelectItem>
              {groups.map(({ district, towns }) => [
                <SelectItem key={district.id} value={district.slug}>
                  {district.name_ar}
                </SelectItem>,
                ...towns.map((town) => (
                  <SelectItem key={town.id} value={town.slug}>
                    {'  '}
                    {town.name_ar}
                  </SelectItem>
                )),
              ])}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-sort">
            {t('directory.sort')}
          </label>
          <Select value={sort} onValueChange={(value) => updateParams({ sort: value })}>
            <SelectTrigger aria-labelledby="filter-sort">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(SORT_KEYS) as SortOption[]).map((option) => (
                <SelectItem key={option} value={option}>
                  {t(SORT_KEYS[option])}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {hasFilters ? (
        <div className="mb-6">
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            <X className="h-4 w-4" aria-hidden="true" />
            {t('states.clearFilters')}
          </Button>
        </div>
      ) : null}

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
  )
}
