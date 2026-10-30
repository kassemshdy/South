import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, ExternalLink, Eye } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { DeleteForeverButton } from '@/features/admin/DeleteForeverButton'
import { useStaffCan } from '@/features/admin/staffAccess'
import { IssueCredentialsCard } from '@/features/admin/IssueCredentialsCard'
import { OwnerIdentityCard } from '@/features/admin/OwnerIdentityCard'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n } from '@/i18n'
import { ApiError, viewAsStorage } from '@/services/api/client'
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
      className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:text-brand-800 hover:underline"
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
        className="shrink-0 text-sm font-semibold text-brand-700 hover:text-brand-800"
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
        className="shrink-0 text-sm font-semibold text-brand-700 hover:text-brand-800"
      >
        {talent.status === 'PENDING_REVIEW' ? t('admin.review') : t('admin.details')}
      </Link>
    </li>
  )
}

export function AdminUserDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
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
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700"
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
        {/* Never an administrator: the API refuses it, and the button would
            only offer a way to lock the platform's owners out. */}
        {data.role !== 'ADMIN' ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <ViewAsButton userId={data.id} />
            <DeleteForeverButton
              size="sm"
              description={t('admin.deleteUserBody')}
              onDelete={() => adminApi.deleteUser(data.id)}
              onDeleted={() => navigate('/admin/users')}
            />
          </div>
        ) : null}
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

      <section className="max-w-md">
        <IssueCredentialsCard
          userId={data.id}
          phoneNumber={data.phone_number}
          isAdmin={data.role === 'ADMIN'}
        />
      </section>

      <section className="max-w-md">
        <OwnerIdentityCard identity={data.identity} />
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

/**
 * Opens the owner's account in this tab, read-only, as the owner sees it
 * (the owners' decision, 29 Oct 2026). For the roles that already read
 * owners' documents; the API refuses the rest, and refuses every change
 * made during the view.
 */
function ViewAsButton({ userId }: { userId: string }) {
  const { t } = useI18n()
  const toast = useToast()
  const allowed = useStaffCan('moderate')
  const open = useMutation({
    mutationFn: () => adminApi.viewAs(userId),
    onSuccess: (session) => {
      const started = viewAsStorage.start({
        token: session.access_token,
        userId: session.user_id,
        name: session.display_name,
        expiresAt: session.expires_at,
        canEdit: session.can_edit,
      })
      if (started) window.location.assign('/dashboard')
      else toast.error(t('viewAs.failed'))
    },
    onError: (error) =>
      toast.error(t('viewAs.failed'), error instanceof ApiError ? error.message : undefined),
  })
  if (!allowed) return null
  return (
    <Button variant="outline" size="sm" loading={open.isPending} onClick={() => open.mutate()}>
      <Eye className="h-4 w-4" aria-hidden="true" />
      {t('viewAs.open')}
    </Button>
  )
}
