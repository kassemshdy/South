import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n } from '@/i18n'
import { adminEmployerRequestsApi } from '@/services/api/endpoints'
import type { EmployerRequest, EmployerRequestStatus } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDateTime, whatsappHref } from '@/utils/format'

const STATUSES: EmployerRequestStatus[] = ['NEW', 'CONTACTED', 'HIRED']

/**
 * Every employer's "have a job for this candidate?" request (the owners'
 * candidate directory ticket, 31 Oct 2026). There is no WhatsApp gateway, so
 * staff relay each one to the candidate from their own WhatsApp -- the link
 * below opens it written -- and mark it contacted, then hired, which is also
 * the platform's count of placements.
 */
export function AdminEmployerRequestsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canAct = useStaffCan('employerRequests')
  const [status, setStatus] = useState<EmployerRequestStatus | undefined>(undefined)

  const requests = useQuery({
    queryKey: ['admin', 'employer-requests', status ?? 'all'],
    queryFn: () => adminEmployerRequestsApi.list(status),
  })
  const move = useMutation({
    mutationFn: ({ id, next }: { id: string; next: EmployerRequestStatus }) =>
      adminEmployerRequestsApi.setStatus(id, next),
    onSuccess: () => {
      toast.success(t('adminCandidate.statusUpdated'))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'employer-requests'] })
    },
    onError: () => toast.error(t('states.errorFallback')),
  })

  const relayText = (entry: EmployerRequest) =>
    t('adminCandidate.relayMessage', {
      name: entry.candidate_name ?? '',
      employer: entry.employer_name,
      company: entry.company ?? '—',
      phone: entry.phone,
      job: entry.job_title ?? '—',
      message: entry.message ?? '—',
    })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('adminCandidate.requestsTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('adminCandidate.requestsIntro')}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {([undefined, ...STATUSES] as const).map((value) => (
          <button
            key={value ?? 'all'}
            type="button"
            aria-pressed={status === value}
            onClick={() => setStatus(value)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
              status === value
                ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
            )}
          >
            {value ? t(`adminCandidate.status.${value}`) : t('adminCandidate.filterAll')}
          </button>
        ))}
      </div>

      {requests.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : requests.isError ? (
        <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
      ) : requests.data && requests.data.length > 0 ? (
        <ul className="space-y-3">
          {requests.data.map((entry) => {
            const relay = whatsappHref(entry.candidate_whatsapp, relayText(entry))
            return (
              <li key={entry.id}>
                <Card>
                  <CardBody className="space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="text-sm text-ink-500">{t('adminCandidate.candidate')}</p>
                        <p className="font-semibold text-ink-900">
                          <bdi>{entry.candidate_name ?? '—'}</bdi>
                        </p>
                        <div className="flex flex-wrap gap-3 text-sm">
                          {entry.candidate_slug ? (
                            <Link
                              to={`/talent/${encodeURIComponent(entry.candidate_slug)}`}
                              className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
                            >
                              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                              {t('adminCandidate.publicPage')}
                            </Link>
                          ) : null}
                          <Link
                            to={`/admin/talent/${entry.profile_id}`}
                            className="font-semibold text-brand-700 hover:underline"
                          >
                            {t('adminCandidate.reviewPage')}
                          </Link>
                        </div>
                      </div>
                      <p className="text-sm text-ink-500">
                        {formatDateTime(entry.created_at, locale)}
                      </p>
                    </div>

                    <dl className="grid gap-2 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-ink-500">{t('adminCandidate.employer')}</dt>
                        <dd className="font-semibold text-ink-900">
                          <bdi>{entry.employer_name}</bdi>{' '}
                          <span className="ltr-nums font-normal text-ink-700" dir="ltr">
                            {entry.phone}
                          </span>
                        </dd>
                      </div>
                      {entry.company ? (
                        <div>
                          <dt className="text-ink-500">{t('adminCandidate.company')}</dt>
                          <dd className="text-ink-900">
                            <bdi>{entry.company}</bdi>
                          </dd>
                        </div>
                      ) : null}
                      {entry.job_title ? (
                        <div>
                          <dt className="text-ink-500">{t('adminCandidate.job')}</dt>
                          <dd className="text-ink-900">
                            <bdi>{entry.job_title}</bdi>
                          </dd>
                        </div>
                      ) : null}
                      {entry.message ? (
                        <div className="sm:col-span-2">
                          <dt className="text-ink-500">{t('adminCandidate.message')}</dt>
                          <dd className="whitespace-pre-line text-ink-900" dir="auto">
                            {entry.message}
                          </dd>
                        </div>
                      ) : null}
                    </dl>

                    <div className="flex flex-wrap items-center gap-3">
                      {relay ? (
                        <Button asChild size="sm">
                          <a href={relay} target="_blank" rel="noreferrer">
                            <MessageCircle className="h-4 w-4" aria-hidden="true" />
                            {t('adminCandidate.relay')}
                          </a>
                        </Button>
                      ) : (
                        <p className="text-sm text-ink-500">
                          {t('adminCandidate.noCandidateNumber')}
                        </p>
                      )}
                      <div className="ms-auto flex items-center gap-2">
                        <span className="text-sm text-ink-500">
                          {t('adminCandidate.statusLabel')}
                        </span>
                        <Select
                          value={entry.status}
                          disabled={!canAct || move.isPending}
                          onValueChange={(next) =>
                            move.mutate({ id: entry.id, next: next as EmployerRequestStatus })
                          }
                        >
                          <SelectTrigger className="w-40">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {STATUSES.map((value) => (
                              <SelectItem key={value} value={value}>
                                {t(`adminCandidate.status.${value}`)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              </li>
            )
          })}
        </ul>
      ) : (
        <EmptyState title={t('adminCandidate.empty')} />
      )}
    </div>
  )
}
