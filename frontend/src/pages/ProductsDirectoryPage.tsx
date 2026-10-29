import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { LocateFixed, SlidersHorizontal, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { ErrorState, NoSearchResults } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { ProductCard } from '@/features/items/ProductCard'
import { PageBanner } from '@/components/layout/PageBanner'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { originFromParams } from '@/features/onboarding/destinations'
import { DisplacedFilterButton } from '@/features/directory/DisplacedFilterButton'
import { useNearestSort } from '@/features/directory/useNearestSort'
import { SearchBox } from '@/features/search/SearchBox'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { trackDirectoryView } from '@/services/analytics'
import { publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { GoodsOrigin, ProductSortOption } from '@/types/api'

const ALL = '__all__'
/**
 * The products themselves, each card a product with its shop (the owners
 * asked for this back on 28 Oct 2026, after a round of listing shops here
 * instead; the shops are at /businesses).
 *
 * Price appears here as two orderings, not as a range.
 *
 * A range needed three controls — a currency, because a bound spanning
 * dollars and lira means two things at once, plus both ends — and a fourth
 * decision about the products whose owner named no price. That is four
 * questions asked before the visitor has seen a result, to narrow a
 * catalogue of 28. Ordering asks none of them: nothing is removed, and an
 * unpriced product sorts to the end rather than being called cheap.
 */
const SORT_KEYS: Record<ProductSortOption, TranslationKey> = {
  newest: 'directory.sortNewest',
  nearest: 'directory.sortNearest',
  rating: 'directory.sortRating',
  name: 'directory.sortName',
  oldest: 'directory.sortOldest',
  price_asc: 'products.sortPriceAsc',
  price_desc: 'products.sortPriceDesc',
}

/**
 * Goods made in the South and imported goods each have their own page, at the
 * CEO's request: `/products/local` and `/products/imported`, headed with the
 * titles he chose for them, each with an address that can be sent to
 * somebody and a page a search engine sees as distinct. They are this
 * directory with the origin fixed, so the two cannot drift apart from each
 * other or from `/products`, which still lists both.
 */
const ORIGIN_PAGES: Record<GoodsOrigin, { titleKey: TranslationKey; path: string }> = {
  LOCAL: { titleKey: 'onboarding.ownerTitle', path: '/products/local' },
  // The CEO's own title for this page, longer than the door's.
  IMPORTED: { titleKey: 'products.importedPageTitle', path: '/products/imported' },
}

export function ProductsDirectoryPage({ fixedOrigin }: { fixedOrigin?: GoodsOrigin } = {}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const originPage = fixedOrigin ? ORIGIN_PAGES[fixedOrigin] : undefined

  const q = searchParams.get('q') ?? ''
  const category = searchParams.get('category') ?? ''
  const location = searchParams.get('location') ?? ''
  const displaced = searchParams.get('displaced') === '1'
  // Fixed by the page on the two origin pages; otherwise an optional filter.
  const origin = fixedOrigin ?? originFromParams(searchParams)
  const chosenSort = searchParams.get('sort') as ProductSortOption | null
  const page = Number(searchParams.get('page') ?? '1')
  // The filters on screen, never the search text: see services/analytics.ts.
  useEffect(() => {
    trackDirectoryView({ directory: 'products', category, location, origin: origin ?? undefined, displaced })
  }, [category, location, origin, displaced])
  const setSort = useCallback(
    (value: ProductSortOption) => {
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
  } = useNearestSort<ProductSortOption>(chosenSort, setSort, 'rating')

  // Open from the start when a query-string origin narrowed the list: on a
  // phone the filters are folded away, and a narrowing nobody can see is a
  // silent one. The origin pages say it in their heading instead.
  const [filtersOpen, setFiltersOpen] = useState(() => Boolean(originFromParams(searchParams)))
  const t = useT()

  const heading = originPage ? t(originPage.titleKey) : t('products.heading')

  useSeo({
    title: q
      ? t('products.seoSearchTitle', { query: q })
      : originPage
        ? `${heading} | ${t('app.name')}`
        : t('products.seoTitle'),
    description: t('products.seoDescription'),
    canonicalPath: originPage?.path ?? '/products',
  })

  const categories = useCategories()
  const { groups } = useLocationGroups()

  const results = useQuery({
    queryKey: queryKeys.products({ q, category, location, origin, displaced, sort, lat: near?.lat, lng: near?.lng, page }),
    queryFn: () =>
      publicItemApi.search({
        q: q || undefined,
        category: category || undefined,
        location: location || undefined,
        origin,
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

  // The page's own origin is not a filter anyone set, so it cannot be cleared.
  const hasFilters =
    Boolean(q || category || location || displaced || (origin && !fixedOrigin)) || chosenSort !== null
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <>
      <PageBanner
        page={
          fixedOrigin === 'LOCAL'
            ? 'products_local'
            : fixedOrigin === 'IMPORTED'
              ? 'products_imported'
              : 'products'
        }
        title={heading}
        subtitle={
          results.data
            ? t('products.resultCount', { count: results.data.meta.total })
            : t('products.introFallback')
        }
      />
      <div className="container-page py-10">
        {/* The other two directories, one tap away. Without this each
            directory was an island: a search that came up empty here left
            the browser's back button as the only way across. */}
        <BrowseSwitcher current="products" />

        {/* The home page's box, suggesting as someone types; a plain search
            narrows this directory rather than leaving it. */}
        <div className="mb-4">
          <SearchBox
            appearance="page"
            value={q}
            label={t('products.searchLabel')}
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

        <div className={`mb-6 grid gap-3 ${fixedOrigin ? 'sm:grid-cols-3' : 'sm:grid-cols-2 lg:grid-cols-4'} ${filtersOpen ? 'grid' : 'hidden sm:grid'}`}>
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
                  .sort((a, b) => b.item_count - a.item_count)
                  .map((item) => (
                  <SelectItem key={item.id} value={item.slug}>
                    {t('directory.categoryWithCount', { name: item.name_ar, count: item.item_count })}
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
              countOf={(node) => node.item_count}
            />
          </div>

          {/* Not on the origin pages, where the page itself is the choice. */}
          {fixedOrigin ? null : (
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-origin">
              {t('directory.origin')}
            </label>
            <Select
              value={origin ?? ALL}
              onValueChange={(value) => updateParams({ origin: value === ALL ? '' : value })}
            >
              <SelectTrigger aria-labelledby="filter-origin">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>{t('directory.allOrigins')}</SelectItem>
                <SelectItem value="LOCAL">{t('directory.originLocal')}</SelectItem>
                <SelectItem value="IMPORTED">{t('onboarding.importedTitle')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="filter-sort">
              {t('directory.sort')}
            </label>
            <Select value={sort} onValueChange={(value) => chooseSort(value as ProductSortOption)}>
              <SelectTrigger aria-labelledby="filter-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(SORT_KEYS) as ProductSortOption[]).map((option) => (
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
                {results.data.items.map((product) => (
                  <ProductCard key={product.id} product={product} />
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

