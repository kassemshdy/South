import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Search, SlidersHorizontal, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { ErrorState, NoSearchResults } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { ProductCard } from '@/features/items/ProductCard'
import { PageBanner } from '@/components/layout/PageBanner'
import { BrowseSwitcher } from '@/features/onboarding/BrowseSwitcher'
import { originFromParams } from '@/features/onboarding/destinations'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { GoodsOrigin, ProductSortOption } from '@/types/api'

const ALL = '__all__'
/**
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
  // Fixed by the page on the two origin pages; otherwise an optional filter.
  const origin = fixedOrigin ?? originFromParams(searchParams)
  const sort = (searchParams.get('sort') as ProductSortOption | null) ?? 'newest'
  const page = Number(searchParams.get('page') ?? '1')

  // Local mirror so typing feels instant; the URL updates on submit, which
  // keeps searches shareable and back/forward working.
  const [searchInput, setSearchInput] = useState(q)
  // Open from the start when a query-string origin narrowed the list: on a
  // phone the filters are folded away, and a narrowing nobody can see is a
  // silent one. The origin pages say it in their heading instead.
  const [filtersOpen, setFiltersOpen] = useState(() => Boolean(originFromParams(searchParams)))
  const t = useT()

  useEffect(() => setSearchInput(q), [q])

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
    queryKey: queryKeys.products({ q, category, location, origin, sort, page }),
    queryFn: () =>
      publicItemApi.search({
        q: q || undefined,
        category: category || undefined,
        location: location || undefined,
        origin,
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

  // The page's own origin is not a filter anyone set, so it cannot be cleared.
  const hasFilters =
    Boolean(q || category || location || (origin && !fixedOrigin)) || sort !== 'newest'
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <>
      <PageBanner
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

        <form
          role="search"
          onSubmit={(event) => {
            event.preventDefault()
            updateParams({ q: searchInput.trim() })
          }}
          className="mb-4 flex gap-2"
        >
          <label htmlFor="products-search" className="sr-only">
            {t('products.searchLabel')}
          </label>
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute inset-y-0 start-4 my-auto h-5 w-5 text-ink-300" aria-hidden="true" />
            <input
              id="products-search"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder={t('products.searchLabel')}
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
                {categories.data?.map((item) => (
                  <SelectItem key={item.id} value={item.slug}>
                    {item.name_ar}
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
                      {'  '}
                      {town.name_ar}
                    </SelectItem>
                  )),
                ])}
              </SelectContent>
            </Select>
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
            <Select value={sort} onValueChange={(value) => updateParams({ sort: value })}>
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

