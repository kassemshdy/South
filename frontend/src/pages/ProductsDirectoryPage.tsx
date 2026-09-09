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
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT, type TranslationKey } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { publicItemApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Currency, SortOption } from '@/types/api'

const ALL = '__all__'
const SORT_KEYS: Record<SortOption, TranslationKey> = {
  newest: 'directory.sortNewest',
  name: 'directory.sortName',
  oldest: 'directory.sortOldest',
}
const CURRENCY_KEYS: Record<Currency, TranslationKey> = {
  USD: 'items.currencyUsd',
  LBP: 'items.currencyLbp',
}

/** A price the API will accept: digits, optionally two decimals, non-negative. */
function cleanAmount(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return ''
  return /^\d+(\.\d{1,2})?$/.test(trimmed) ? trimmed : ''
}

export function ProductsDirectoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const category = searchParams.get('category') ?? ''
  const location = searchParams.get('location') ?? ''
  const sort = (searchParams.get('sort') as SortOption | null) ?? 'newest'
  const page = Number(searchParams.get('page') ?? '1')

  // Price is three parameters, not two. A range across USD and LBP is
  // meaningless — this directory holds both and no exchange rate — so the
  // API refuses a bound without a currency, and the UI makes that visible by
  // not letting one be typed until a currency is picked, rather than sending
  // a request it knows will 422.
  const currency = (searchParams.get('currency') as Currency | null) ?? null
  const minPrice = currency ? cleanAmount(searchParams.get('min_price') ?? '') : ''
  const maxPrice = currency ? cleanAmount(searchParams.get('max_price') ?? '') : ''
  // Absent means true: a product whose owner left the price blank stays in
  // the results unless the visitor says otherwise. Dropping it silently
  // would penalise them for an empty field.
  const includeUnpriced = searchParams.get('include_unpriced') !== 'false'
  const rangeInverted =
    minPrice !== '' && maxPrice !== '' && Number(minPrice) > Number(maxPrice)

  // Local mirror so typing feels instant; the URL updates on submit, which
  // keeps searches shareable and back/forward working.
  const [searchInput, setSearchInput] = useState(q)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const t = useT()

  useEffect(() => setSearchInput(q), [q])

  useSeo({
    title: q ? t('products.seoSearchTitle', { query: q }) : t('products.seoTitle'),
    description: t('products.seoDescription'),
    canonicalPath: '/products',
  })

  const categories = useCategories()
  const { groups } = useLocationGroups()

  const priceQuery = {
    currency: currency ?? undefined,
    min_price: minPrice || undefined,
    max_price: maxPrice || undefined,
    // Only sent when it is doing something, so the common URL stays short.
    include_unpriced: includeUnpriced ? undefined : false,
  }

  const results = useQuery({
    queryKey: queryKeys.products({ q, category, location, sort, page, ...priceQuery }),
    queryFn: () =>
      publicItemApi.search({
        q: q || undefined,
        category: category || undefined,
        location: location || undefined,
        ...priceQuery,
        sort,
        page,
        page_size: 12,
      }),
    placeholderData: keepPreviousData,
    // An inverted range is refused by the API too; catching it here keeps a
    // typo from clearing the results and showing an error banner instead.
    enabled: !rangeInverted,
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

  const hasFilters =
    Boolean(q || category || location || currency) || sort !== 'newest' || !includeUnpriced
  const resetFilters = () => setSearchParams(new URLSearchParams())

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="text-3xl">{t('products.heading')}</h1>
        <p className="mt-2 text-ink-500">
          {results.data
            ? t('products.resultCount', { count: results.data.meta.total })
            : t('products.introFallback')}
        </p>
      </header>

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
            className="h-12 w-full rounded-xl border-2 border-ink-100 bg-white ps-12 pe-4 text-[15px] placeholder:text-ink-300 focus:border-clay-400 focus:outline-none focus:ring-2 focus:ring-clay-500/20"
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

      <div className={`mb-6 ${filtersOpen ? 'block' : 'hidden sm:block'}`}>
        <fieldset className="rounded-xl border border-ink-100 bg-sand-50/60 p-4">
          <legend className="px-1 text-sm font-semibold text-ink-700">
            {t('products.priceHeading')}
          </legend>

          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1.5 block text-sm text-ink-500" id="filter-currency">
                {t('items.currencyLabel')}
              </label>
              <Select
                value={currency ?? ALL}
                onValueChange={(value) =>
                  // Clearing the currency clears the bounds with it: a range
                  // left behind with nothing to denominate it is exactly the
                  // meaningless comparison this filter refuses to make.
                  updateParams(
                    value === ALL
                      ? { currency: '', min_price: '', max_price: '' }
                      : { currency: value },
                  )
                }
              >
                <SelectTrigger aria-labelledby="filter-currency">
                  <SelectValue placeholder={t('products.priceCurrencyAll')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>{t('products.priceCurrencyAll')}</SelectItem>
                  {(Object.keys(CURRENCY_KEYS) as Currency[]).map((code) => (
                    <SelectItem key={code} value={code}>
                      {t(CURRENCY_KEYS[code])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm text-ink-500" htmlFor="filter-min-price">
                {t('products.priceMinLabel')}
              </label>
              <PriceInput
                id="filter-min-price"
                value={minPrice}
                disabled={currency === null}
                onCommit={(value) => updateParams({ min_price: value })}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm text-ink-500" htmlFor="filter-max-price">
                {t('products.priceMaxLabel')}
              </label>
              <PriceInput
                id="filter-max-price"
                value={maxPrice}
                disabled={currency === null}
                onCommit={(value) => updateParams({ max_price: value })}
              />
            </div>
          </div>

          {currency === null ? (
            <p className="mt-2 text-sm text-ink-500">{t('products.priceCurrencyFirst')}</p>
          ) : null}
          {rangeInverted ? (
            <p className="mt-2 text-sm font-semibold text-clay-700" role="alert">
              {t('products.priceRangeInvalid')}
            </p>
          ) : null}

          <label className="mt-3 flex items-start gap-2.5 text-sm text-ink-700">
            <input
              type="checkbox"
              checked={includeUnpriced}
              onChange={(event) =>
                updateParams({ include_unpriced: event.target.checked ? '' : 'false' })
              }
              className="mt-0.5 h-4 w-4 shrink-0 rounded border-ink-300 text-clay-600 focus:ring-clay-500/30"
            />
            <span>
              {t('products.includeUnpriced')}
              <span className="block text-ink-500">{t('products.includeUnpricedHint')}</span>
            </span>
          </label>
        </fieldset>
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
        {rangeInverted ? (
          <p className="rounded-xl bg-sand-50 p-4 text-ink-600">
            {t('products.priceRangeInvalid')}
          </p>
        ) : results.isLoading ? (
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
  )
}


/**
 * A price box that writes to the URL on blur or Enter, not on every keystroke.
 *
 * Typing "45" through a URL-backed value would otherwise fire a search for
 * "4" first, and each of those is a page of results the visitor never asked
 * for. A blank or malformed entry commits as empty, which removes the bound
 * rather than sending something the API would refuse.
 */
function PriceInput({
  id,
  value,
  disabled,
  onCommit,
}: {
  id: string
  value: string
  disabled: boolean
  onCommit: (value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  useEffect(() => setDraft(value), [value])

  const commit = () => {
    const cleaned = cleanAmount(draft)
    setDraft(cleaned)
    if (cleaned !== value) onCommit(cleaned)
  }

  return (
    <input
      id={id}
      type="text"
      inputMode="decimal"
      dir="ltr"
      value={draft}
      disabled={disabled}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          event.preventDefault()
          commit()
        }
      }}
      className="ltr-nums h-11 w-full rounded-xl border-2 border-ink-100 bg-white px-3 text-[15px] focus:border-clay-400 focus:outline-none focus:ring-2 focus:ring-clay-500/20 disabled:cursor-not-allowed disabled:bg-ink-50 disabled:text-ink-300"
    />
  )
}
