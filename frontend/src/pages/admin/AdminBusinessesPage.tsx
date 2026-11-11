import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { Pagination } from '@/features/businesses/Pagination'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, type AdminBusinessSort } from '@/services/api/endpoints'
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
  const category = searchParams.get('category') ?? ''
  const location = searchParams.get('location') ?? ''
  const { t, locale } = useI18n()
  const sortParam = searchParams.get('sort')
  const sort: AdminBusinessSort =
    sortParam === 'instagram' || sortParam === 'facebook' ? sortParam : 'newest'
  const canRefreshFollowers = useStaffCan('manage')
  const canModerate = useStaffCan('moderate')
  const toast = useToast()
  const queryClient = useQueryClient()
  // Drafts the owner never sent sit unseen; staff move them into the queue
  // (the owners' request, 10 Nov 2026). A reviewer then finishes them.
  const afterSend = (message: string) => {
    toast.success(message)
    void queryClient.invalidateQueries({ queryKey: ['admin', 'businesses'] })
  }
  const sendToReview = useMutation({
    mutationFn: (id: string) => adminApi.sendToReview(id),
    onSuccess: () => afterSend(t('admin.sentToReview')),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })
  const sendAllDrafts = useMutation({
    mutationFn: adminApi.sendAllDraftsToReview,
    onSuccess: (result) => afterSend(result.message),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })
  const refreshFollowers = useMutation({
    mutationFn: adminApi.refreshFollowers,
    onSuccess: (result) => toast.success(result.message),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })
  const [searchInput, setSearchInput] = useState(q)

  // Follow the address when it changes from outside (a link, the back
  // button), but never undo what is being typed: a trailing space the search
  // trimmed away is still the admin's.
  useEffect(() => setSearchInput((current) => (current.trim() === q ? current : q)), [q])

  // Search as the admin types, a moment after they stop, as the accounts
  // list does. Like pressing Enter, a search covers every status.
  useEffect(() => {
    const query = searchInput.trim()
    if (query === q) return
    const timer = window.setTimeout(() => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current)
          if (query) {
            next.set('q', query)
            next.set('status', 'ALL')
          } else next.delete('q')
          next.delete('page')
          return next
        },
        { replace: true },
      )
    }, 300)
    return () => window.clearTimeout(timer)
  }, [searchInput, q, setSearchParams])

  const results = useQuery({
    queryKey: [
      ...queryKeys.adminBusinesses(statusParam === 'ALL' ? undefined : status, page, q),
      sort,
      category,
      location,
    ],
    queryFn: () =>
      adminApi.businesses({
        ...(statusParam === 'ALL' ? {} : { status }),
        ...(q ? { q } : {}),
        ...(sort === 'newest' ? {} : { sort }),
        ...(category ? { category } : {}),
        ...(location ? { location } : {}),
        page,
        page_size: 20,
      }),
    placeholderData: keepPreviousData,
  })

  // Category and place, every one listed with its shops of any status, empty
  // ones too (the owners' request, 11 Nov 2026).
  const categories = useQuery({ queryKey: queryKeys.adminCategories, queryFn: adminApi.categories })
  const locations = useQuery({ queryKey: queryKeys.adminLocations, queryFn: adminApi.locations })
  const locationGroups = useMemo(() => {
    const all = locations.data ?? []
    return all
      .filter((node) => node.type === 'DISTRICT')
      .map((district) => ({ district, towns: all.filter((node) => node.parent_id === district.id) }))
  }, [locations.data])

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
        {canModerate && statusParam === 'DRAFT' ? (
          <Button
            size="sm"
            variant="outline"
            loading={sendAllDrafts.isPending}
            onClick={() => {
              if (window.confirm(t('admin.sendAllDraftsConfirm'))) sendAllDrafts.mutate()
            }}
          >
            {t('admin.sendAllDrafts')}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="admin-filter-category">
            {t('directory.category')}
          </label>
          <Select
            value={category || '__all__'}
            onValueChange={(value) => update({ category: value === '__all__' ? '' : value })}
          >
            <SelectTrigger aria-labelledby="admin-filter-category">
              <SelectValue placeholder={t('directory.allCategories')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">{t('directory.allCategories')}</SelectItem>
              {(categories.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.slug}>
                  {t('directory.categoryWithCount', { name: item.name_ar, count: item.business_count })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" htmlFor="admin-filter-location">
            {t('directory.location')}
          </label>
          <LocationCombobox
            id="admin-filter-location"
            by="slug"
            emptyLabel={t('directory.allLocations')}
            placeholder={t('directory.allLocations')}
            value={location}
            onChange={(value) => update({ location: value })}
            groups={locationGroups}
            countOf={(node) => node.business_count}
            showEmpty
          />
        </div>
      </div>

      {/* Sort by followers (the owners' request, 9 Nov 2026); the counts are
          read daily through Apify, and a manager can refresh them now. */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-ink-500">{t('adminFollowers.sortLabel')}</span>
        {(
          [
            ['newest', 'adminFollowers.sortNewest'],
            ['instagram', 'adminFollowers.sortInstagram'],
            ['facebook', 'adminFollowers.sortFacebook'],
          ] as const
        ).map(([value, labelKey]) => (
          <button
            key={value}
            type="button"
            aria-pressed={sort === value}
            onClick={() => update({ sort: value === 'newest' ? '' : value })}
            className={cn(
              'rounded-full px-3 py-1.5 text-sm font-semibold transition-colors',
              sort === value
                ? 'bg-brand-800 text-white'
                : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
            )}
          >
            {t(labelKey)}
          </button>
        ))}
        {canRefreshFollowers ? (
          <Button
            variant="ghost"
            size="sm"
            loading={refreshFollowers.isPending}
            onClick={() => refreshFollowers.mutate()}
          >
            {t('adminFollowers.refresh')}
          </Button>
        ) : null}
      </div>

      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          // A search covers every status, not the tab that happens to be open:
          // a reviewer looking up a number expects to find the account
          // wherever it is (the owners' ticket, 29 Oct 2026).
          const query = searchInput.trim()
          update(query ? { q: query, status: 'ALL' } : { q: '' })
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
                          {business.instagram_followers != null ||
                          business.facebook_followers != null ? (
                            <p className="ltr-nums text-xs font-semibold text-ink-500">
                              {[
                                business.instagram_followers != null
                                  ? t('adminFollowers.instagram', {
                                      count: business.instagram_followers.toLocaleString('en'),
                                    })
                                  : null,
                                business.facebook_followers != null
                                  ? t('adminFollowers.facebook', {
                                      count: business.facebook_followers.toLocaleString('en'),
                                    })
                                  : null,
                              ]
                                .filter(Boolean)
                                .join(' · ')}
                            </p>
                          ) : null}
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

                      {canModerate &&
                      (business.status === 'DRAFT' || business.status === 'REJECTED') ? (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={sendToReview.isPending && sendToReview.variables === business.id}
                          onClick={() => sendToReview.mutate(business.id)}
                        >
                          {t('admin.sendToReview')}
                        </Button>
                      ) : null}
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
