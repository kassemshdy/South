import { MessageCircle, PhoneCall } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useI18n, type TranslationKey } from '@/i18n'
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
 * One order: who asked, for what, and the ways to answer them.
 *
 * Shared by the owner's orders tab, the page an order link opens, and the
 * administrators' list. `onMove` is the owner's alone -- without it the card
 * is read-only, which is what an administrator gets.
 */
export function OrderCard({
  order,
  businessName,
  onMove,
  moving = false,
  heading,
}: {
  order: Order
  businessName: string
  onMove?: ((status: OrderStatus) => void) | undefined
  moving?: boolean
  /** Shown above the customer, e.g. which shop the order is for. */
  heading?: ReactNode
}) {
  const { t, locale } = useI18n()
  const reply = whatsappHref(
    order.customer_phone,
    t('orders.replyMessage', { name: order.customer_name, business: businessName }),
  )

  return (
    <div className="rounded-xl border border-ink-100 p-4">
      {heading}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{order.customer_name}</span>
        <Badge className={STATUS_TONE[order.status]}>{t(STATUS_LABEL[order.status])}</Badge>
        <span className="text-xs text-ink-300">{formatDate(order.created_at, locale)}</span>
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
        <p className="mt-2 rounded-lg bg-sand-50 p-2.5 text-sm text-ink-600">{order.note}</p>
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

        {onMove && order.status === 'NEW' ? (
          <Button size="sm" variant="ghost" loading={moving} onClick={() => onMove('CONTACTED')}>
            {t('orders.markContacted')}
          </Button>
        ) : null}
        {onMove && order.status !== 'DONE' ? (
          <Button size="sm" variant="ghost" loading={moving} onClick={() => onMove('DONE')}>
            {t('orders.markDone')}
          </Button>
        ) : null}
      </div>
    </div>
  )
}
