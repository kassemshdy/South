import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { MessageCircle, Phone, Store } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { Pagination } from '@/features/businesses/Pagination'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { formatRelativeDate, telHref, whatsappHref } from '@/utils/format'

const PAGE_SIZE = 25

/**
 * Approved shops with nothing on sale, for staff to contact (the owners'
 * request, 3 Nov 2026). They are not counted on the public pages until they
 * add a product, so this is the list of shops to follow up with.
 */
export function AdminShopsWithoutProductsPage() {
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const shops = useQuery({
    queryKey: ['admin', 'businesses', 'without-products', page],
    queryFn: () =>
      adminApi.businesses({
        status: 'APPROVED',
        without_products: true,
        page,
        page_size: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl">{t('adminShops.noProductsTitle')}</h1>
        <p className="mt-1 text-ink-500">
          {shops.data
            ? t('adminShops.noProductsIntro', { count: shops.data.meta.total })
            : t('adminShops.noProductsIntroLoading')}
        </p>
      </header>

      {shops.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : shops.isError ? (
        <ErrorState error={shops.error} onRetry={() => void shops.refetch()} />
      ) : shops.data && shops.data.items.length === 0 ? (
        <EmptyState icon={<Store className="h-6 w-6" aria-hidden="true" />} title={t('adminShops.noProductsEmpty')} />
      ) : shops.data ? (
        <>
          <Card>
            <CardBody className="p-2">
              <ul className="divide-y divide-ink-100">
                {shops.data.items.map((shop) => {
                  const number = shop.whatsapp ?? shop.phone ?? shop.owner_phone
                  const wa = whatsappHref(
                    number,
                    t('adminShops.noProductsWhatsapp', { name: shop.name }),
                  )
                  const call = telHref(shop.phone ?? shop.owner_phone)
                  return (
                    <li
                      key={shop.id}
                      className="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
                    >
                      <div className="min-w-0">
                        <Link
                          to={`/admin/businesses/${shop.id}`}
                          className="font-semibold hover:text-brand-700"
                          dir="auto"
                        >
                          {shop.name}
                        </Link>
                        <p className="text-sm text-ink-500">
                          {[shop.category?.name_ar, shop.location?.name_ar]
                            .filter(Boolean)
                            .join(' · ')}
                        </p>
                        <p className="ltr-nums text-xs text-ink-400">
                          {number ? <span dir="ltr">{number}</span> : null}
                          {number ? ' · ' : null}
                          {t('adminShops.approvedOn', {
                            date: formatRelativeDate(shop.approved_at ?? shop.created_at, locale, t),
                          })}
                        </p>
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
                            {t('admin.workshopContact')}
                          </a>
                        ) : null}
                        {call ? (
                          <a
                            href={call}
                            className="inline-flex min-h-9 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-brand-700 hover:bg-sand-100"
                          >
                            <Phone className="h-4 w-4" aria-hidden="true" />
                            {t('adminShops.call')}
                          </a>
                        ) : null}
                      </div>
                    </li>
                  )
                })}
              </ul>
            </CardBody>
          </Card>
          <Pagination meta={shops.data.meta} onChange={setPage} />
        </>
      ) : null}
    </div>
  )
}
