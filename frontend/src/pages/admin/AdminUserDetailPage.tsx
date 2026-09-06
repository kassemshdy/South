import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ExternalLink } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminBusiness, AdminTalent } from '@/types/api'
import { formatDate } from '@/utils/format'

function WebsiteLink({ website }: { website: string | null }) {
  const { t } = useI18n()
  if (!website) return null
  return (
    <a
      href={website}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm font-semibold text-clay-600 hover:text-clay-700 hover:underline"
    >
      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
      {t('admin.fieldWebsite')}
    </a>
  )
}

function BusinessRow({ business }: { business: AdminBusiness }) {
  const { t } = useI18n()
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate font-semibold">{business.name}</p>
          <StatusBadge status={business.status} />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <p className="truncate text-sm text-ink-500">
            {business.category?.name_ar ?? t('common.dash')} ·{' '}
            {business.location?.name_ar ?? t('common.dash')}
          </p>
          <WebsiteLink website={business.website} />
        </div>
      </div>
      <Link
        to={`/admin/businesses/${business.id}`}
        className="shrink-0 text-sm font-semibold text-clay-600 hover:text-clay-700"
      >
        {business.status === 'PENDING_REVIEW' ? t('admin.review') : t('admin.details')}
      </Link>
    </li>
  )
}

function TalentRow({ talent }: { talent: AdminTalent }) {
  const { t } = useI18n()
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate font-semibold">{talent.display_name}</p>
          <StatusBadge status={talent.status} />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <p className="truncate text-sm text-ink-500">
            {talent.skill?.name_ar ?? t('common.dash')} ·{' '}
            {talent.location?.name_ar ?? t('common.dash')}
          </p>
          <WebsiteLink website={talent.website} />
        </div>
      </div>
      <Link
        to={`/admin/talent/${talent.id}`}
        className="shrink-0 text-sm font-semibold text-clay-600 hover:text-clay-700"
      >
        {talent.status === 'PENDING_REVIEW' ? t('admin.review') : t('admin.details')}
      </Link>
    </li>
  )
}

export function AdminUserDetailPage() {
  const { id = '' } = useParams()
  const { t, locale } = useI18n()

  const user = useQuery({
    queryKey: queryKeys.adminUser(id),
    queryFn: () => adminApi.user(id),
    enabled: id.length > 0,
  })

  if (user.isLoading) return <Skeleton className="h-96 rounded-2xl" />
  if (user.isError) return <ErrorState error={user.error} onRetry={() => void user.refetch()} />

  const data = user.data
  if (!data) return null

  return (
    <div className="max-w-3xl space-y-6">
      <Link
        to="/admin/users"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-clay-600"
      >
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t('admin.backToUsers')}
      </Link>

      <header>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl">
            {data.display_name ?? data.phone_number ?? data.email ?? t('admin.userNoName')}
          </h1>
          {data.role === 'ADMIN' ? (
            <Badge className="bg-olive-100 text-olive-700">{t('admin.roleAdmin')}</Badge>
          ) : null}
          {!data.is_active ? (
            <Badge className="bg-ink-100 text-ink-700">{t('admin.userSuspended')}</Badge>
          ) : null}
        </div>
        <p className="ltr-nums mt-1 text-sm text-ink-500">
          {data.phone_number ?? data.email ?? t('common.dash')} ·{' '}
          {t('admin.userJoined', { date: formatDate(data.created_at, locale) })}
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">{t('admin.userBusinessesHeading')}</h2>
        {data.businesses.length > 0 ? (
          <Card>
            <CardBody className="p-2">
              <ul className="divide-y divide-ink-100">
                {data.businesses.map((business) => (
                  <BusinessRow key={business.id} business={business} />
                ))}
              </ul>
            </CardBody>
          </Card>
        ) : (
          <p className="text-sm text-ink-500">{t('admin.userNoBusinesses')}</p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">{t('admin.userTalentHeading')}</h2>
        {data.talent_profile ? (
          <Card>
            <CardBody className="p-2">
              <ul className="divide-y divide-ink-100">
                <TalentRow talent={data.talent_profile} />
              </ul>
            </CardBody>
          </Card>
        ) : (
          <p className="text-sm text-ink-500">{t('admin.userNoTalent')}</p>
        )}
      </section>
    </div>
  )
}
