import { useQuery } from '@tanstack/react-query'
import { ExternalLink, MessageCircle, MousePointerClick, Phone, ShoppingBag, Store } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ContactedShop } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatRelativeDate, telHref, whatsappHref } from '@/utils/format'

const PERIODS = [30, 90, 365] as const

/**
 * Shops that visitors reached through the site -- a press of the WhatsApp
 * or call button on the shop's page, or an order -- for staff to ask their
 * owners for a video or a testimonial (the owners' request, 9 Nov 2026).
 * The counter knows how many presses, never who pressed, so this lists
 * shops, not the visitors.
 */
export function AdminContactedShopsPage() {
  const { t, locale } = useI18n()
  const [days, setDays] = useState<(typeof PERIODS)[number]>(90)
  const shops = useQuery({
    queryKey: queryKeys.adminContactedShops(days),
    queryFn: () => adminApi.contactedShops(days),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl">{t('adminContacted.title')}</h1>
        <p className="mt-1 max-w-2xl text-ink-500">{t('adminContacted.subtitle')}</p>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label={t('adminContacted.period')}>
        {PERIODS.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={days === value}
            onClick={() => setDays(value)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-sm font-semibold',
              days === value
                ? 'border-brand-800 bg-brand-800 text-white'
                : 'border-ink-100 bg-white text-ink-700 hover:border-brand-300',
            )}
          >
            {t('adminContacted.lastDays', { count: value })}
          </button>
        ))}
      </div>

      {shops.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : shops.isError ? (
        <ErrorState error={shops.error} onRetry={() => void shops.refetch()} />
      ) : !shops.data?.length ? (
        <EmptyState
          icon={<Store className="h-7 w-7" aria-hidden="true" />}
          title={t('adminContacted.empty')}
        />
      ) : (
        <Card>
          <CardBody className="p-0">
            <p className="border-b border-ink-100 px-4 py-3 text-sm font-semibold text-ink-700">
              {t('adminContacted.count', { count: shops.data.length })}
            </p>
            <ul className="divide-y divide-ink-100">
              {shops.data.map((shop) => (
                <ShopRow key={shop.id} shop={shop} locale={locale} />
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

function ShopRow({
  shop,
  locale,
}: {
  shop: ContactedShop
  locale: Parameters<typeof formatRelativeDate>[1]
}) {
  const { t } = useI18n()
  const wa = whatsappHref(shop.owner_phone, t('adminContacted.whatsapp'))
  const call = telHref(shop.owner_phone)

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        {shop.logo_url ? (
          <img src={shop.logo_url} alt="" className="h-11 w-11 shrink-0 rounded-xl object-cover" />
        ) : (
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sand-100">
            <Store className="h-5 w-5 text-ink-400" aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0">
          <Link
            to={`/admin/businesses/${shop.id}`}
            className="font-semibold hover:text-brand-700"
            dir="auto"
          >
            {shop.name}
          </Link>
          <p className="ltr-nums flex flex-wrap items-center gap-x-3 text-sm text-ink-500">
            <span className="inline-flex items-center gap-1">
              <MousePointerClick className="h-4 w-4" aria-hidden="true" />
              {t('adminContacted.clicks', { count: shop.contact_clicks })}
            </span>
            {shop.orders > 0 ? (
              <span className="inline-flex items-center gap-1">
                <ShoppingBag className="h-4 w-4" aria-hidden="true" />
                {t('adminContacted.orders', { count: shop.orders })}
              </span>
            ) : null}
            <span>
              {t('adminContacted.lastContact', {
                date: formatRelativeDate(shop.last_contact, locale, t),
              })}
            </span>
          </p>
          {shop.owner_phone ? (
            <p className="ltr-nums text-xs text-ink-400" dir="ltr">
              {shop.owner_phone}
            </p>
          ) : null}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {wa ? (
          <a
            href={wa}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-9 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-olive-700 hover:bg-sand-100"
          >
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            {t('adminContacted.askButton')}
          </a>
        ) : null}
        {call ? (
          <a
            href={call}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-brand-700 hover:bg-sand-100"
          >
            <Phone className="h-4 w-4" aria-hidden="true" />
            {t('adminContacted.call')}
          </a>
        ) : null}
        <a
          href={`/business/${shop.slug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-9 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-ink-600 hover:bg-sand-100"
        >
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          {t('adminContacted.openPage')}
        </a>
      </div>
    </li>
  )
}
