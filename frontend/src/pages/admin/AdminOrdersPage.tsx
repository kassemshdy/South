import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { OrderCard } from '@/features/cart/OrderCard'
import { useT, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { OrderStatus } from '@/types/api'
import { cn } from '@/utils/cn'

const FILTERS: { value: OrderStatus | undefined; labelKey: TranslationKey }[] = [
  { value: undefined, labelKey: 'admin.ordersFilterAll' },
  { value: 'NEW', labelKey: 'orders.statusNEW' },
  { value: 'CONTACTED', labelKey: 'orders.statusCONTACTED' },
  { value: 'DONE', labelKey: 'orders.statusDONE' },
]

/**
 * Every order on every listing, newest first (the owners' decision, so
 * orders can be followed up with the shops).
 *
 * Read-only: replying and moving an order along stay with the shop's owner.
 * An administrator can still call or message the customer from the card.
 */
export function AdminOrdersPage() {
  const t = useT()
  const [status, setStatus] = useState<OrderStatus | undefined>(undefined)

  const orders = useQuery({
    queryKey: queryKeys.adminOrders(status),
    queryFn: () => adminApi.orders(status),
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.ordersHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.ordersSubtitle')}</p>
      </header>

      <div className="flex flex-wrap gap-2" role="group" aria-label={t('admin.ordersHeading')}>
        {FILTERS.map((filter) => (
          <button
            key={filter.labelKey}
            type="button"
            aria-pressed={status === filter.value}
            onClick={() => setStatus(filter.value)}
            className={cn(
              'rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors',
              status === filter.value
                ? 'bg-brand-700 text-white'
                : 'bg-white text-ink-600 ring-1 ring-ink-100 hover:bg-sand-50',
            )}
          >
            {t(filter.labelKey)}
          </button>
        ))}
      </div>

      {orders.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : orders.isError ? (
        <ErrorState error={orders.error} onRetry={() => void orders.refetch()} />
      ) : orders.data && orders.data.length > 0 ? (
        <ul className="space-y-3">
          {orders.data.map((order) => (
            <li key={order.id}>
              <OrderCard
                order={order}
                businessName={order.business_name}
                heading={
                  <p className="mb-2 text-sm">
                    <Link
                      to={`/admin/businesses/${order.business_id}`}
                      className="font-semibold text-brand-800 hover:underline"
                    >
                      {order.business_name}
                    </Link>
                  </p>
                }
              />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('admin.ordersEmpty')} />
      )}
    </div>
  )
}
