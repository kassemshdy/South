import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, PhoneCall } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { serviceRequestApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, telHref, whatsappHref } from '@/utils/format'
import type { OrderStatus, ServiceRequest } from '@/types/api'

const STATUS_LABEL: Record<OrderStatus, TranslationKey> = {
  NEW: 'serviceRequests.statusNEW',
  CONTACTED: 'serviceRequests.statusCONTACTED',
  DONE: 'serviceRequests.statusDONE',
}

const STATUS_TONE: Record<OrderStatus, string> = {
  NEW: 'bg-wheat-100 text-wheat-700',
  CONTACTED: 'bg-brand-100 text-brand-800',
  DONE: 'bg-ink-100 text-ink-600',
}

/**
 * Service requests as the provider sees them — the same screen `OwnerOrders`
 * gives a shop, which is the whole point of the feature: a craftsperson used
 * to get a WhatsApp link and no record.
 *
 * No profile id anywhere: a talent profile is one-per-account, so the token
 * is the lookup key and there is no id a caller could substitute.
 *
 * The intro says out loud that nothing pings them, because it doesn't: there
 * is no email infrastructure here and a Twilio message costs money per
 * request, so this slice records the request and leaves the notification to
 * the requester's own WhatsApp message. Someone who believes they will be
 * alerted and is not would rather have been told.
 */
export function OwnerServiceRequests() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()

  const requests = useQuery({
    queryKey: queryKeys.myServiceRequests,
    queryFn: serviceRequestApi.listMine,
  })

  const move = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OrderStatus }) =>
      serviceRequestApi.setStatus(id, status),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.myServiceRequests }),
    onError: (error) =>
      toast.error(
        t('serviceRequests.updateFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  if (requests.isLoading) return <Skeleton className="h-40 rounded-2xl" />
  if (requests.isError) {
    return <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
  }

  const rows: ServiceRequest[] = requests.data ?? []

  return (
    <div>
      <h3 className="font-bold">{t('serviceRequests.ownerHeading')}</h3>
      <p className="mt-1 text-sm text-ink-500">{t('serviceRequests.ownerIntro')}</p>

      {rows.length === 0 ? (
        <p className="mt-4 rounded-xl bg-sand-50 p-4 text-sm text-ink-500">
          {t('serviceRequests.ownerEmpty')}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((request) => {
            const reply = whatsappHref(
              request.customer_phone,
              t('serviceRequests.replyMessage', { name: request.customer_name }),
            )
            return (
              <li key={request.id} className="rounded-xl border border-ink-100 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{request.customer_name}</span>
                  <Badge className={STATUS_TONE[request.status]}>
                    {t(STATUS_LABEL[request.status])}
                  </Badge>
                  <span className="text-xs text-ink-300">
                    {formatDate(request.created_at, locale)}
                  </span>
                </div>

                {/* Written by a stranger, so it carries its own direction. */}
                <p
                  className="mt-2 whitespace-pre-line rounded-lg bg-sand-50 p-2.5 text-sm leading-relaxed text-ink-700"
                  dir="auto"
                >
                  {request.details}
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  {reply ? (
                    <Button asChild size="sm">
                      <a href={reply} target="_blank" rel="noreferrer noopener">
                        <MessageCircle className="h-4 w-4" aria-hidden="true" />
                        {t('serviceRequests.reply')}
                      </a>
                    </Button>
                  ) : null}
                  <Button asChild size="sm" variant="outline">
                    <a href={telHref(request.customer_phone) ?? '#'} className="ltr-nums">
                      <PhoneCall className="h-4 w-4" aria-hidden="true" />
                      {request.customer_phone}
                    </a>
                  </Button>

                  {request.status === 'NEW' ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={move.isPending}
                      onClick={() => move.mutate({ id: request.id, status: 'CONTACTED' })}
                    >
                      {t('serviceRequests.markContacted')}
                    </Button>
                  ) : null}
                  {request.status !== 'DONE' ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={move.isPending}
                      onClick={() => move.mutate({ id: request.id, status: 'DONE' })}
                    >
                      {t('serviceRequests.markDone')}
                    </Button>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
