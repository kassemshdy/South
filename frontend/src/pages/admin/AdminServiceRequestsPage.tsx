import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, MessageCircle, Phone, RotateCcw, Search, Trash2, Wrench } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import type { AdminOpenServiceRequest } from '@/types/api'
import { formatDateTime, telHref, whatsappHref } from '@/utils/format'

/**
 * Visitors' "request a service" (the owners' services redesign, 3 Nov 2026):
 * what they need, where, and how to reach them. Staff find a provider --
 * "find providers" opens the services directory filtered to the request --
 * put them in touch, and archive the request.
 */
export function AdminServiceRequestsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canHandle = useStaffCan('support')
  const [solved, setSolved] = useState(false)
  const requests = useQuery({
    queryKey: ['admin', 'service-requests', solved],
    queryFn: () => adminApi.serviceRequests(solved),
  })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['admin', 'service-requests'] })
  const onError = (error: unknown) =>
    toast.error(t('admin.actionFailed'), error instanceof ApiError ? error.message : undefined)
  const solve = useMutation({ mutationFn: adminApi.solveServiceRequest, onSuccess: refresh, onError })
  const reopen = useMutation({ mutationFn: adminApi.reopenServiceRequest, onSuccess: refresh, onError })
  const remove = useMutation({ mutationFn: adminApi.deleteServiceRequest, onSuccess: refresh, onError })

  const providersLink = (request: AdminOpenServiceRequest) => {
    const params = new URLSearchParams()
    if (request.skill_slug) params.set('skill', request.skill_slug)
    if (request.location_slug) params.set('location', request.location_slug)
    const query = params.toString()
    return query ? `/services?${query}` : '/services'
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('openRequest.adminTitle')}</h1>
          <p className="mt-2 text-ink-500">{t('openRequest.adminSubtitle')}</p>
        </div>
        <div className="flex gap-1.5" role="group">
          {[false, true].map((value) => (
            <button
              key={String(value)}
              type="button"
              aria-pressed={solved === value}
              onClick={() => setSolved(value)}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ${
                solved === value ? 'bg-brand-800 text-white' : 'bg-sand-100 text-ink-600 hover:bg-sand-200'
              }`}
            >
              {t(value ? 'openRequest.tabArchive' : 'openRequest.tabOpen')}
            </button>
          ))}
        </div>
      </header>

      {requests.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : requests.isError ? (
        <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
      ) : !requests.data || requests.data.length === 0 ? (
        <EmptyState
          icon={<Wrench className="h-7 w-7" aria-hidden="true" />}
          title={t(solved ? 'openRequest.emptyArchive' : 'openRequest.emptyOpen')}
        />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {requests.data.map((request) => {
            const wa = whatsappHref(request.customer_phone)
            const call = telHref(request.customer_phone)
            return (
              <li key={request.id}>
                <Card className="h-full">
                  <CardBody className="flex h-full flex-col gap-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-bold text-ink-900" dir="auto">
                          {request.customer_name}
                        </p>
                        <p className="ltr-nums text-sm text-ink-500" dir="ltr">
                          {request.customer_phone}
                        </p>
                      </div>
                      <span className="text-xs text-ink-400">
                        {formatDateTime(request.created_at, locale)}
                      </span>
                    </div>
                    <p className="whitespace-pre-line text-ink-700" dir="auto">
                      {request.details}
                    </p>
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      {request.skill_name ? (
                        <span className="rounded-full bg-sand-100 px-2.5 py-1 font-medium text-brand-700">
                          {request.skill_name}
                        </span>
                      ) : null}
                      {request.location_name ? (
                        <span className="rounded-full bg-sand-100 px-2.5 py-1 font-medium text-ink-600">
                          {request.location_name}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-auto flex flex-wrap items-center gap-2 border-t border-ink-100 pt-3">
                      <Button asChild size="sm">
                        <Link to={providersLink(request)} target="_blank">
                          <Search className="h-4 w-4" aria-hidden="true" />
                          {t('openRequest.findProviders')}
                        </Link>
                      </Button>
                      {wa ? (
                        <Button asChild size="sm" variant="outline">
                          <a href={wa} target="_blank" rel="noopener noreferrer">
                            <MessageCircle className="h-4 w-4" aria-hidden="true" />
                            {t('admin.workshopContact')}
                          </a>
                        </Button>
                      ) : null}
                      {call ? (
                        <Button asChild size="sm" variant="ghost">
                          <a href={call}>
                            <Phone className="h-4 w-4" aria-hidden="true" />
                            {t('adminShops.call')}
                          </a>
                        </Button>
                      ) : null}
                      {canHandle ? (
                        <div className="ms-auto flex gap-1">
                          {solved ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => reopen.mutate(request.id)}
                              aria-label={t('openRequest.reopen')}
                            >
                              <RotateCcw className="h-4 w-4" aria-hidden="true" />
                            </Button>
                          ) : (
                            <Button size="sm" variant="outline" onClick={() => solve.mutate(request.id)}>
                              <Archive className="h-4 w-4" aria-hidden="true" />
                              {t('openRequest.solve')}
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-clay-600"
                            onClick={() => {
                              if (window.confirm(t('openRequest.confirmDelete'))) remove.mutate(request.id)
                            }}
                            aria-label={t('openRequest.delete')}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  </CardBody>
                </Card>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
