import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, MessageCircle, Pencil, Phone, RotateCcw, Store } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { Pagination } from '@/features/businesses/Pagination'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import type { AdminBusiness } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatRelativeDate, telHref, whatsappHref } from '@/utils/format'

const PAGE_SIZE = 25
const LIST_KEY = ['admin', 'businesses', 'without-products'] as const

type Tab = 'todo' | 'done'

/**
 * Approved shops with nothing on sale, for staff to contact (the owners'
 * request, 3 Nov 2026). They are not counted on the public pages until they
 * add a product, so this is the list of shops to follow up with. Staff mark
 * a shop contacted, with a note, and the two tabs split the list by that
 * (the owners' request, 6 Nov 2026).
 */
export function AdminShopsWithoutProductsPage() {
  const { t, locale } = useI18n()
  const [tab, setTab] = useState<Tab>('todo')
  const [page, setPage] = useState(1)
  const contacted = tab === 'done'

  const count = (done: boolean) =>
    adminApi.businesses({
      status: 'APPROVED',
      without_products: true,
      contacted: done,
      page: 1,
      page_size: 1,
    })
  const todoCount = useQuery({ queryKey: [...LIST_KEY, 'count', false], queryFn: () => count(false) })
  const doneCount = useQuery({ queryKey: [...LIST_KEY, 'count', true], queryFn: () => count(true) })
  const shops = useQuery({
    queryKey: [...LIST_KEY, tab, page],
    queryFn: () =>
      adminApi.businesses({
        status: 'APPROVED',
        without_products: true,
        contacted,
        page,
        page_size: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  })

  const total =
    todoCount.data && doneCount.data ? todoCount.data.meta.total + doneCount.data.meta.total : null
  const tabs: { id: Tab; label: string }[] = [
    { id: 'todo', label: t('adminShops.tabNotContacted', { count: todoCount.data?.meta.total ?? '…' }) },
    { id: 'done', label: t('adminShops.tabContacted', { count: doneCount.data?.meta.total ?? '…' }) },
  ]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl">{t('adminShops.noProductsTitle')}</h1>
        <p className="mt-1 text-ink-500">
          {total !== null
            ? t('adminShops.noProductsIntro', { count: total })
            : t('adminShops.noProductsIntroLoading')}
        </p>
      </header>

      <div className="flex flex-wrap gap-2" role="tablist">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => {
              setTab(item.id)
              setPage(1)
            }}
            className={cn(
              'ltr-nums rounded-full border-2 px-4 py-1.5 text-sm font-semibold transition-colors',
              tab === item.id
                ? 'border-brand-700 bg-brand-700 text-white'
                : 'border-ink-100 bg-white text-ink-700 hover:border-brand-300',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {shops.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : shops.isError ? (
        <ErrorState error={shops.error} onRetry={() => void shops.refetch()} />
      ) : shops.data && shops.data.items.length === 0 ? (
        <EmptyState
          icon={<Store className="h-6 w-6" aria-hidden="true" />}
          title={contacted ? t('adminShops.contactedEmpty') : t('adminShops.noProductsEmpty')}
        />
      ) : shops.data ? (
        <>
          <Card>
            <CardBody className="p-2">
              <ul className="divide-y divide-ink-100">
                {shops.data.items.map((shop) => (
                  <ShopRow key={shop.id} shop={shop} locale={locale} />
                ))}
              </ul>
            </CardBody>
          </Card>
          <Pagination meta={shops.data.meta} onChange={setPage} />
        </>
      ) : null}
    </div>
  )
}

function ShopRow({ shop, locale }: { shop: AdminBusiness; locale: Parameters<typeof formatRelativeDate>[1] }) {
  const { t } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canMark = useStaffCan('credentials')
  const [editing, setEditing] = useState(false)
  const [note, setNote] = useState(shop.outreach_note ?? '')

  const number = shop.whatsapp ?? shop.phone ?? shop.owner_phone
  const wa = whatsappHref(number, t('adminShops.noProductsWhatsapp', { name: shop.name }))
  const call = telHref(shop.phone ?? shop.owner_phone)
  const contacted = Boolean(shop.outreach_contacted_at)

  const save = useMutation({
    mutationFn: (body: { contacted: boolean; note?: string | null }) =>
      adminApi.setOutreach(shop.id, body),
    onSuccess: () => {
      setEditing(false)
      void queryClient.invalidateQueries({ queryKey: LIST_KEY })
    },
    onError: (error) =>
      toast.error(t('adminShops.outreachFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <li className="space-y-3 px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <Link
            to={`/admin/businesses/${shop.id}`}
            className="font-semibold hover:text-brand-700"
            dir="auto"
          >
            {shop.name}
          </Link>
          <p className="text-sm text-ink-500">
            {[shop.category?.name_ar, shop.location?.name_ar].filter(Boolean).join(' · ')}
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
          {canMark && !contacted && !editing ? (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              {t('adminShops.markContacted')}
            </Button>
          ) : null}
        </div>
      </div>

      {contacted && !editing ? (
        <div className="rounded-xl bg-olive-50 px-3 py-2 text-sm">
          <p className="font-semibold text-olive-700">
            {t('adminShops.contactedOn', {
              date: formatRelativeDate(shop.outreach_contacted_at as string, locale, t),
            })}
          </p>
          {shop.outreach_note ? (
            <p className="mt-1 whitespace-pre-line text-ink-700" dir="auto">
              {shop.outreach_note}
            </p>
          ) : null}
          {canMark ? (
            <div className="mt-2 flex flex-wrap gap-1">
              <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {t('adminShops.editNote')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                loading={save.isPending}
                onClick={() => save.mutate({ contacted: false })}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                {t('adminShops.unmarkContacted')}
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {editing ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate({ contacted: true, note })
          }}
        >
          <Textarea
            rows={2}
            dir="auto"
            maxLength={2000}
            value={note}
            placeholder={t('adminShops.notePlaceholder')}
            aria-label={t('adminShops.notePlaceholder')}
            onChange={(event) => setNote(event.target.value)}
          />
          <div className="flex gap-2">
            <Button type="submit" size="sm" loading={save.isPending}>
              {t('adminShops.saveNote')}
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(false)}>
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      ) : null}
    </li>
  )
}
