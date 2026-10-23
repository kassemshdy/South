import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate, useParams } from 'react-router-dom'

import { BackLink } from '@/components/ui/BackLink'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { OrderCard } from '@/features/cart/OrderCard'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { orderApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { OrderStatus } from '@/types/api'

/**
 * The page an order link opens: the link a customer sends the shop on
 * WhatsApp after ordering.
 *
 * Behind a sign-in, and the API answers 404 to everybody but the shop's
 * owner, so the link is safe to sit in a chat. An administrator who follows
 * one is sent to the orders list, where every order is.
 */
export function OrderPage() {
  const { id = '' } = useParams()
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'

  useSeo({ title: t('orders.ownerHeading'), noIndex: true })

  const order = useQuery({
    queryKey: queryKeys.myOrder(id),
    queryFn: () => orderApi.getMine(id),
    enabled: id.length > 0 && !isAdmin,
  })

  const move = useMutation({
    mutationFn: (status: OrderStatus) => {
      if (!order.data) throw new Error('no order')
      return orderApi.setStatus(order.data.business_id, id, status)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.myOrder(id) })
      if (order.data) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.myOrders(order.data.business_id),
        })
      }
    },
    onError: (error) =>
      toast.error(t('orders.updateFailed'), error instanceof ApiError ? error.message : undefined),
  })

  if (isAdmin) return <Navigate to="/admin/orders" replace />

  return (
    <div className="container-page max-w-2xl py-10">
      <BackLink fallback="/dashboard" />
      <h1 className="mb-4 mt-4 text-2xl">{t('orders.ownerHeading')}</h1>
      {order.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : order.isError || !order.data ? (
        <ErrorState error={order.error} onRetry={() => void order.refetch()} />
      ) : (
        <>
          <OrderCard
            order={order.data}
            businessName={order.data.business_name}
            moving={move.isPending}
            onMove={(status) => move.mutate(status)}
            heading={
              <p className="mb-2 text-sm font-semibold text-brand-800">{order.data.business_name}</p>
            }
          />
          <p className="mt-4 text-sm">
            <Link
              to={`/dashboard/businesses/${order.data.business_id}/edit?tab=orders`}
              className="text-brand-700 hover:underline"
            >
              {t('orders.linkAllOrders')}
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
