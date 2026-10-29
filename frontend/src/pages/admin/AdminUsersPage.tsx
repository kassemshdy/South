import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { useI18n } from '@/i18n'
import { adminApi, type AdminUserFilters } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

const FIELD =
  'rounded-xl border border-ink-100 bg-white px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none'

/**
 * Every account, found by phone (however it is typed) or by name -- the
 * account's own or its shop's -- and narrowed by role and status, in a
 * chosen order (the owners' request, 29 Oct 2026).
 */
export function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const { t, locale } = useI18n()
  const [typed, setTyped] = useState('')
  const [filters, setFilters] = useState<AdminUserFilters>({ sort: 'newest' })

  // Search as the admin types, a moment after they stop.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => ({ ...current, q: typed.trim() || undefined }))
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [typed])

  const change = (next: Partial<AdminUserFilters>) => {
    setFilters((current) => ({ ...current, ...next }))
    setPage(1)
  }

  const users = useQuery({
    queryKey: queryKeys.adminUsers(page, { ...filters }),
    queryFn: () => adminApi.users(page, filters),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.usersHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.usersSubtitle')}</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto_auto]">
        <label className="relative">
          <span className="sr-only">{t('admin.usersSearch')}</span>
          <Search
            className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400"
            aria-hidden="true"
          />
          <input
            type="search"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            placeholder={t('admin.usersSearch')}
            className={`${FIELD} w-full ps-9`}
          />
        </label>
        <select
          aria-label={t('admin.usersRoleFilter')}
          className={FIELD}
          value={filters.role ?? ''}
          onChange={(event) =>
            change({ role: (event.target.value || undefined) as AdminUserFilters['role'] })
          }
        >
          <option value="">{t('admin.usersAllRoles')}</option>
          <option value="OWNER">{t('admin.usersOwners')}</option>
          <option value="ADMIN">{t('admin.roleAdmin')}</option>
        </select>
        <select
          aria-label={t('admin.usersStatusFilter')}
          className={FIELD}
          value={filters.active === undefined ? '' : String(filters.active)}
          onChange={(event) =>
            change({ active: event.target.value === '' ? undefined : event.target.value === 'true' })
          }
        >
          <option value="">{t('admin.usersAllStatuses')}</option>
          <option value="true">{t('admin.usersActive')}</option>
          <option value="false">{t('admin.userSuspended')}</option>
        </select>
        <select
          aria-label={t('admin.usersSort')}
          className={FIELD}
          value={filters.sort ?? 'newest'}
          onChange={(event) => change({ sort: event.target.value as AdminUserFilters['sort'] })}
        >
          <option value="newest">{t('admin.usersSortNewest')}</option>
          <option value="oldest">{t('admin.usersSortOldest')}</option>
          <option value="name">{t('admin.usersSortName')}</option>
          <option value="listings">{t('admin.usersSortListings')}</option>
        </select>
      </div>
      {users.data ? (
        <p className="text-sm text-ink-500">
          {t('admin.usersTotal', { count: users.data.meta.total })}
        </p>
      ) : null}

      {users.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : users.data && users.data.items.length > 0 ? (
        <>
          <Card>
            <CardBody className="p-2">
              <ul className="divide-y divide-ink-100">
                {users.data.items.map((user) => (
                  <li key={user.id}>
                    <Link
                      to={`/admin/users/${user.id}`}
                      className="flex flex-wrap items-center justify-between gap-3 px-3 py-3 transition-colors hover:bg-sand-50"
                    >
                      <div>
                        <p className="ltr-nums font-semibold">{user.phone_number ?? user.email ?? '—'}</p>
                        <p className="text-sm text-ink-500">
                          {user.display_name ?? t('admin.userNoName')} ·{' '}
                          {t('admin.userJoined', { date: formatDate(user.created_at, locale) })}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {user.role === 'ADMIN' ? (
                          <Badge className="bg-olive-100 text-olive-700">
                            {t('admin.roleAdmin')}
                          </Badge>
                        ) : (
                          <Badge className="bg-sand-100 text-brand-700">
                            {t('admin.userBusinessCount', { count: user.business_count })}
                          </Badge>
                        )}
                        {!user.is_active ? (
                          <Badge className="bg-ink-100 text-ink-700">
                            {t('admin.userSuspended')}
                          </Badge>
                        ) : null}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
          <Pagination meta={users.data.meta} onChange={setPage} />
        </>
      ) : (
        <EmptyState title={t('admin.usersEmpty')} />
      )}
    </div>
  )
}
