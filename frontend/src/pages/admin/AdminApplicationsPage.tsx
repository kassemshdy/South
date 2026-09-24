import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { DiscardedApplication } from '@/types/api'
import { formatDate } from '@/utils/format'

/**
 * Applications that arrived for a phone number that already has an account.
 *
 * The public form answers them like any other and acts on none of them --
 * that is what stops it being a way to ask which numbers are registered, or
 * to put a listing in somebody else's dashboard. They used to be thrown
 * away; at the CEO's request they wait here instead, so a real owner who
 * applied twice is not silently lost. Handling one is a conversation with the
 * account holder, outside this site, so the only action here is to mark it
 * handled.
 */
export function AdminApplicationsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [includeDismissed, setIncludeDismissed] = useState(false)

  const applications = useQuery({
    queryKey: queryKeys.adminDiscardedApplications(includeDismissed),
    queryFn: () => adminApi.discardedApplications(includeDismissed),
  })

  const dismiss = useMutation({
    mutationFn: (id: string) => adminApi.dismissApplication(id),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['admin', 'discarded-applications'] }),
    onError: () => toast.error(t('admin.applicationsActionFailed')),
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.applicationsHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.applicationsSubtitle')}</p>
      </header>

      <label className="flex items-center gap-2 text-sm text-ink-700">
        <input
          type="checkbox"
          checked={includeDismissed}
          onChange={(event) => setIncludeDismissed(event.target.checked)}
        />
        {t('admin.applicationsShowDismissed')}
      </label>

      {applications.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : applications.isError ? (
        <ErrorState error={applications.error} onRetry={() => void applications.refetch()} />
      ) : applications.data && applications.data.length > 0 ? (
        <ul className="space-y-3">
          {applications.data.map((entry: DiscardedApplication) => {
            const listing = entry.payload.business ?? null
            const talent = entry.payload.talent ?? null
            const title = listing?.name ?? talent?.display_name ?? ''
            const about =
              listing?.short_description ?? listing?.description ?? talent?.bio ?? null
            return (
              <li key={entry.id}>
                <Card>
                  <CardBody className="space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-ink-900" dir="auto">
                          {title}
                        </p>
                        <p className="mt-0.5 text-sm text-ink-500">
                          <span dir="auto">{entry.payload.identity?.full_name ?? ''}</span>
                          {' · '}
                          <span dir="ltr" className="ltr-nums">
                            {entry.login_phone}
                          </span>
                          {' · '}
                          {formatDate(entry.created_at, locale)}
                        </p>
                      </div>
                      <Badge className="bg-sand-100 text-clay-700">
                        {t(entry.kind === 'BUSINESS' ? 'onboarding.ownerShort' : 'onboarding.talentShort')}
                      </Badge>
                    </div>

                    {about ? (
                      <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                        {about}
                      </p>
                    ) : null}

                    <div className="flex flex-wrap items-center justify-between gap-2">
                      {entry.existing_user_id ? (
                        <Link
                          to={`/admin/users/${entry.existing_user_id}`}
                          className="text-sm font-semibold text-brand-700 hover:underline"
                        >
                          {t('admin.applicationsExistingAccount')}
                        </Link>
                      ) : (
                        <span />
                      )}
                      {entry.dismissed_at ? (
                        <Badge className="bg-ink-100 text-ink-700">
                          {t('admin.applicationsDismissed')}
                        </Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={dismiss.isPending && dismiss.variables === entry.id}
                          onClick={() => dismiss.mutate(entry.id)}
                        >
                          <Check className="h-4 w-4" aria-hidden="true" />
                          {t('admin.applicationsDismiss')}
                        </Button>
                      )}
                    </div>
                  </CardBody>
                </Card>
              </li>
            )
          })}
        </ul>
      ) : (
        <EmptyState title={t('admin.applicationsEmpty')} />
      )}
    </div>
  )
}
