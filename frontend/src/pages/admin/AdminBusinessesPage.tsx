import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { BusinessStatus } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatRelativeDate, STATUS_KEYS } from '@/utils/format'

const FILTERS: { value: BusinessStatus | 'ALL'; labelKey: TranslationKey }[] = [
  { value: 'PENDING_REVIEW', labelKey: 'admin.filterPending' },
  { value: 'APPROVED', labelKey: 'admin.filterApproved' },
  { value: 'REJECTED', labelKey: 'admin.filterRejected' },
  { value: 'SUSPENDED', labelKey: 'admin.filterSuspended' },
  { value: 'DRAFT', labelKey: 'admin.filterDrafts' },
  { value: 'ALL', labelKey: 'admin.filterAll' },
]

export function AdminBusinessesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const statusParam = searchParams.get('status')
  const status = (statusParam as BusinessStatus | null) ?? 'PENDING_REVIEW'
  const page = Number(searchParams.get('page') ?? '1')
  const q = searchParams.get('q') ?? ''
  const [searchInput, setSearchInput] = useState(q)
  const { t, locale } = useI18n()

  useEffect(() => setSearchInput(q), [q])

  const results = useQuery({
    queryKey: queryKeys.adminBusinesses(statusParam === 'ALL' ? undefined : status, page, q),
    queryFn: () =>
      adminApi.businesses({
        ...(statusParam === 'ALL' ? {} : { status }),
        ...(q ? { q } : {}),
        page,
        page_size: 20,
      }),
    placeholderData: keepPreviousData,
  })

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.businessesHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.businessesSubtitle')}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => {
          const isActive = (statusParam ?? 'PENDING_REVIEW') === filter.value
          return (
            <button
              key={filter.value}
              type="button"
              onClick={() => update({ status: filter.value })}
              aria-pressed={isActive}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
                isActive
                  ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                  : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
              )}
            >
              {t(filter.labelKey)}
            </button>
          )
        })}
      </div>

      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          update({ q: searchInput.trim() })
        }}
        className="flex gap-2"
      >
        <label htmlFor="admin-search" className="sr-only">
          {t('admin.searchLabel')}
        </label>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute inset-y-0 start-4 my-auto h-5 w-5 text-ink-300" aria-hidden="true" />
          <input
            id="admin-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t('admin.searchPlaceholder')}
            className="h-11 w-full rounded-xl border-2 border-ink-100 bg-white ps-12 pe-4 focus:border-brand-400 focus:outline-none"
          />
        </div>
        <Button type="submit">{t('common.search')}</Button>
      </form>

      <div aria-live="polite" aria-busy={results.isFetching}>
        {results.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-20 rounded-2xl" />
            ))}
          </div>
        ) : results.isError ? (
          <ErrorState error={results.error} onRetry={() => void results.refetch()} />
        ) : results.data && results.data.items.length > 0 ? (
          <>
            <ul className="space-y-3">
              {results.data.items.map((business) => (
                <li key={business.id}>
                  <Card>
                    <CardBody className="flex flex-wrap items-center justify-between gap-3 p-4">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-sand-100">
                          {business.logo_url ? (
                            <img src={business.logo_url} alt="" className="h-full w-full object-cover" />
                          ) : null}
                        </div>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate font-bold">{business.name}</p>
                            <StatusBadge status={business.status} />
                          </div>
                          <p className="truncate text-sm text-ink-500">
                            {business.category?.name_ar ?? t('common.dash')} ·{' '}
                            {business.location?.name_ar ?? t('common.dash')} ·{' '}
                            <span className="ltr-nums">
                              {business.owner_phone ?? t('common.dash')}
                            </span>
                          </p>
                          <p className="text-xs text-ink-300">
                            {business.status === 'PENDING_REVIEW'
                              ? t('admin.submittedAgo', {
                                  date: formatRelativeDate(business.submitted_at, locale, t),
                                })
                              : t('admin.createdAgo', {
                                  date: formatRelativeDate(business.created_at, locale, t),
                                })}
                          </p>
                        </div>
                      </div>

                      <Button asChild size="sm">
                        <Link to={`/admin/businesses/${business.id}`}>
                          {business.status === 'PENDING_REVIEW'
                            ? t('admin.review')
                            : t('admin.details')}
                        </Link>
                      </Button>
                    </CardBody>
                  </Card>
                </li>
              ))}
            </ul>
            <Pagination meta={results.data.meta} onChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState
            title={t('admin.listEmptyTitle', {
              status: statusParam === 'ALL' ? t('admin.filterAll') : t(STATUS_KEYS[status]),
            })}
            description={t('admin.listEmptyDescription')}
          />
        )}
      </div>
    </div>
  )
}
