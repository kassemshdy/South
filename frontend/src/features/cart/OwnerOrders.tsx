import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { OrderCard } from '@/features/cart/OrderCard'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { orderApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Order, OrderStatus } from '@/types/api'

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
  const t = useT()
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
          {rows.map((order) => (
            <li key={order.id} id={`order-${order.id}`}>
              <OrderCard
                order={order}
                businessName={businessName}
                moving={move.isPending}
                onMove={(status) => move.mutate({ id: order.id, status })}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
