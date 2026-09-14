import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, Clock, PauseCircle, Package, Store, Users, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatRelativeDate } from '@/utils/format'

export function AdminDashboardPage() {
  const { t, locale } = useI18n()
  const stats = useQuery({ queryKey: queryKeys.adminStats, queryFn: adminApi.stats })
  const pending = useQuery({ queryKey: queryKeys.adminBusinesses('PENDING_REVIEW', 1), queryFn: () => adminApi.pending(1) })

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">{t('admin.dashboardHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.dashboardSubtitle')}</p>
      </header>

      {/* The review queue is the primary admin workflow, so it leads the page. */}
      <Card className="border-clay-200 bg-clay-50/40">
        <CardBody>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-clay-500 text-white">
                <Clock className="h-7 w-7" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold text-clay-700">{t('admin.pendingLabel')}</p>
                <p className="text-3xl font-bold text-clay-900">
                  {stats.isLoading ? '—' : (stats.data?.pending_businesses ?? 0)}
                </p>
              </div>
            </div>
            <Button asChild size="lg">
              <Link to="/admin/businesses?status=PENDING_REVIEW">
                {t('admin.reviewRequests')}
                <ArrowLeft className="h-5 w-5" aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </CardBody>
      </Card>

      {stats.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : stats.isError ? (
        <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />
      ) : stats.data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t('admin.statTotal')} value={stats.data.total_businesses} icon={Store} />
          <StatCard label={t('admin.statApproved')} value={stats.data.approved_businesses} icon={CheckCircle2} tone="text-olive-600" />
          <StatCard label={t('admin.statRejected')} value={stats.data.rejected_businesses} icon={XCircle} tone="text-clay-600" />
          <StatCard label={t('admin.statSuspended')} value={stats.data.suspended_businesses} icon={PauseCircle} tone="text-ink-500" />
          <StatCard label={t('admin.statDrafts')} value={stats.data.draft_businesses} icon={Store} tone="text-ink-500" />
          <StatCard label={t('admin.statUsers')} value={stats.data.total_users} icon={Users} />
          <StatCard label={t('admin.statAdmins')} value={stats.data.total_admins} icon={Users} />
          <StatCard label={t('admin.statItems')} value={stats.data.total_items} icon={Package} />
        </div>
      ) : null}

      <section>
        <h2 className="mb-4 text-xl">{t('admin.latestRequests')}</h2>
        {pending.isLoading ? (
          <Skeleton className="h-40 rounded-2xl" />
        ) : pending.isError ? (
          <ErrorState error={pending.error} onRetry={() => void pending.refetch()} />
        ) : pending.data && pending.data.items.length > 0 ? (
          <ul className="space-y-3">
            {pending.data.items.slice(0, 5).map((business) => (
              <li key={business.id}>
                <Card>
                  <CardBody className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-sand-100">
                        {business.logo_url ? (
                          <img src={business.logo_url} alt="" className="h-full w-full object-cover" />
                        ) : null}
                      </div>
                      <div>
                        <p className="font-bold">{business.name}</p>
                        <p className="text-sm text-ink-500">
                          {business.category?.name_ar ?? t('common.dash')} ·{' '}
                          {business.location?.name_ar ?? t('common.dash')} ·{' '}
                          {formatRelativeDate(business.submitted_at, locale, t)}
                        </p>
                      </div>
                    </div>
                    <Button asChild size="sm">
                      <Link to={`/admin/businesses/${business.id}`}>{t('admin.review')}</Link>
                    </Button>
                  </CardBody>
                </Card>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title={t('admin.queueEmpty')}
            description={t('admin.queueEmptyDescription')}
          />
        )}
      </section>
    </div>
  )
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone = 'text-brand-700',
}: {
  label: string
  value: number
  icon: typeof Store
  tone?: string
}) {
  return (
    <Card>
      <CardBody className="p-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-10 w-10 items-center justify-center rounded-xl bg-sand-100 ${tone}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm text-ink-500">{label}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
