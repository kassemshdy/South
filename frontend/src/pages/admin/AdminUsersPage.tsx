import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

export function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const { t, locale } = useI18n()

  const users = useQuery({
    queryKey: queryKeys.adminUsers(page),
    queryFn: () => adminApi.users(page),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.usersHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.usersSubtitle')}</p>
      </header>

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
