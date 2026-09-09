import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, PhoneCall } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { orderApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, formatPrice, telHref, whatsappHref } from '@/utils/format'
import type { Currency, Order, OrderStatus } from '@/types/api'

const STATUS_LABEL: Record<OrderStatus, TranslationKey> = {
  NEW: 'orders.statusNEW',
  CONTACTED: 'orders.statusCONTACTED',
  DONE: 'orders.statusDONE',
}

const STATUS_TONE: Record<OrderStatus, string> = {
  NEW: 'bg-wheat-100 text-wheat-700',
  CONTACTED: 'bg-brand-100 text-brand-800',
  DONE: 'bg-ink-100 text-ink-600',
}

/**
 * Orders as the owner sees them.
 *
 * The intro says out loud that nothing pings them, because it doesn't:
 * there is no email infrastructure here and a Twilio message costs money per
 * order, so this slice records the request and leaves the notification to
 * the buyer's WhatsApp message. An owner who believes they will be alerted
 * and is not would rather have been told.
 */
export function OwnerOrders({
  businessId,
  businessName,
}: {
  businessId: string
  businessName: string
}) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()

  const orders = useQuery({
    queryKey: queryKeys.myOrders(businessId),
    queryFn: () => orderApi.listMine(businessId),
  })

  const move = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OrderStatus }) =>
      orderApi.setStatus(businessId, id, status),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.myOrders(businessId) }),
    onError: (error) =>
      toast.error(
        t('orders.updateFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  if (orders.isLoading) return <Skeleton className="h-40 rounded-2xl" />
  if (orders.isError) {
    return <ErrorState error={orders.error} onRetry={() => void orders.refetch()} />
  }

  const rows: Order[] = orders.data ?? []

  return (
    <div>
      <h3 className="font-bold">{t('orders.ownerHeading')}</h3>
      <p className="mt-1 text-sm text-ink-500">{t('orders.ownerIntro')}</p>

      {rows.length === 0 ? (
        <p className="mt-4 rounded-xl bg-sand-50 p-4 text-sm text-ink-500">
          {t('orders.ownerEmpty')}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((order) => {
            const reply = whatsappHref(
              order.customer_phone,
              t('orders.replyMessage', {
                name: order.customer_name,
                business: businessName,
              }),
            )
            return (
              <li key={order.id} className="rounded-xl border border-ink-100 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{order.customer_name}</span>
                  <Badge className={STATUS_TONE[order.status]}>
                    {t(STATUS_LABEL[order.status])}
                  </Badge>
                  <span className="text-xs text-ink-300">
                    {formatDate(order.created_at, locale)}
                  </span>
                </div>

                <ul className="mt-2 space-y-0.5 text-sm text-ink-700">
                  {order.lines.map((line, index) => (
                    <li key={index} className="flex justify-between gap-3">
                      <span>
                        {line.title}
                        <span className="ms-1.5 text-ink-400 ltr-nums">× {line.quantity}</span>
                      </span>
                      {line.price ? (
                        <span className="ltr-nums text-ink-500">
                          {formatPrice(line.price, line.currency as Currency)}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>

                {order.note ? (
                  <p className="mt-2 rounded-lg bg-sand-50 p-2.5 text-sm text-ink-600">
                    {order.note}
                  </p>
                ) : null}

                <div className="mt-3 flex flex-wrap gap-2">
                  {reply ? (
                    <Button asChild size="sm">
                      <a href={reply} target="_blank" rel="noreferrer noopener">
                        <MessageCircle className="h-4 w-4" aria-hidden="true" />
                        {t('orders.reply')}
                      </a>
                    </Button>
                  ) : null}
                  <Button asChild size="sm" variant="outline">
                    <a href={telHref(order.customer_phone) ?? '#'} className="ltr-nums">
                      <PhoneCall className="h-4 w-4" aria-hidden="true" />
                      {order.customer_phone}
                    </a>
                  </Button>

                  {order.status === 'NEW' ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={move.isPending}
                      onClick={() => move.mutate({ id: order.id, status: 'CONTACTED' })}
                    >
                      {t('orders.markContacted')}
                    </Button>
                  ) : null}
                  {order.status !== 'DONE' ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={move.isPending}
                      onClick={() => move.mutate({ id: order.id, status: 'DONE' })}
                    >
                      {t('orders.markDone')}
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
