import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, ImageUp, Package, Pencil, Search, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { Pagination } from '@/features/businesses/Pagination'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminItem, GoodsOrigin } from '@/types/api'
import { formatPrice, formatRelativeDate } from '@/utils/format'

const ALL = '__all__'
const PAGE_SIZE = 25
const LIST_KEY = ['admin', 'items'] as const

/**
 * Every product on the site, for staff to find and correct (the owners'
 * request, 11 Nov 2026). Hidden products and ones without a photo are listed
 * too: they are what staff come here to fix. Reviewers and the manager may
 * change them; other staff only look.
 */
export function AdminProductsPage() {
  const { t, locale } = useI18n()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const availability = params.get('available') ?? ''
  const noPhoto = params.get('no_photo') === '1'
  const shop = params.get('shop') ?? ''
  const page = Number(params.get('page') ?? '1')
  const canEdit = useStaffCan('moderate')

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  // Search as staff type, a moment after they stop, as the shops list does.
  const [searchInput, setSearchInput] = useState(q)
  useEffect(() => setSearchInput((current) => (current.trim() === q ? current : q)), [q])
  useEffect(() => {
    const query = searchInput.trim()
    if (query === q) return
    const timer = window.setTimeout(() => update({ q: query }), 300)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput, q])

  const categories = useQuery({ queryKey: queryKeys.adminCategories, queryFn: adminApi.categories })
  const results = useQuery({
    queryKey: [...LIST_KEY, { q, category, availability, noPhoto, shop, page }],
    queryFn: () =>
      adminApi.items({
        q: q || undefined,
        category: category || undefined,
        shop: shop || undefined,
        available: availability === '' ? undefined : availability === 'yes',
        no_photo: noPhoto || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('adminProducts.heading')}</h1>
        <p className="mt-2 text-ink-500">{t('adminProducts.subtitle')}</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative sm:col-span-2">
          <label htmlFor="admin-products-search" className="mb-1.5 block text-sm font-semibold text-ink-700">
            {t('adminProducts.search')}
          </label>
          <Search className="pointer-events-none absolute bottom-3 start-3 h-4 w-4 text-ink-300" aria-hidden="true" />
          <Input
            id="admin-products-search"
            className="ps-9"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t('adminProducts.searchPlaceholder')}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="admin-products-category">
            {t('directory.category')}
          </label>
          <Select value={category || ALL} onValueChange={(value) => update({ category: value === ALL ? '' : value })}>
            <SelectTrigger aria-labelledby="admin-products-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t('directory.allCategories')}</SelectItem>
              {(categories.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.slug}>
                  {item.name_ar}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="admin-products-available">
            {t('adminProducts.availability')}
          </label>
          <Select
            value={availability || ALL}
            onValueChange={(value) => update({ available: value === ALL ? '' : value })}
          >
            <SelectTrigger aria-labelledby="admin-products-available">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t('adminProducts.availabilityAll')}</SelectItem>
              <SelectItem value="yes">{t('adminProducts.availabilityShown')}</SelectItem>
              <SelectItem value="no">{t('adminProducts.availabilityHidden')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant={noPhoto ? 'primary' : 'outline'}
          aria-pressed={noPhoto}
          onClick={() => update({ no_photo: noPhoto ? '' : '1' })}
        >
          {t('adminProducts.noPhoto')}
        </Button>
        {shop ? (
          <Button size="sm" variant="ghost" onClick={() => update({ shop: '' })}>
            {t('adminProducts.allShops')}
          </Button>
        ) : null}
        {results.data ? (
          <span className="text-sm text-ink-500">
            {t('adminProducts.count', { count: results.data.meta.total })}
          </span>
        ) : null}
      </div>

      {results.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : results.isError ? (
        <ErrorState error={results.error} onRetry={() => void results.refetch()} />
      ) : results.data && results.data.items.length > 0 ? (
        <>
          <ul className="space-y-3">
            {results.data.items.map((row) => (
              <li key={row.item.id}>
                <ProductRow row={row} canEdit={canEdit} locale={locale} onShop={(id) => update({ shop: id })} />
              </li>
            ))}
          </ul>
          <Pagination meta={results.data.meta} onChange={(next) => update({ page: String(next) })} />
        </>
      ) : (
        <EmptyState
          icon={<Package className="h-7 w-7" aria-hidden="true" />}
          title={t('adminProducts.empty')}
        />
      )}
    </div>
  )
}

function ProductRow({
  row,
  canEdit,
  locale,
  onShop,
}: {
  row: AdminItem
  canEdit: boolean
  locale: Parameters<typeof formatRelativeDate>[1]
  onShop: (shopId: string) => void
}) {
  const { t } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [editing, setEditing] = useState(false)
  const { item, shop } = row
  const price = formatPrice(item.price, item.currency)

  const refresh = () => void queryClient.invalidateQueries({ queryKey: LIST_KEY })
  const fail = (error: unknown) =>
    toast.error(t('states.errorFallback'), error instanceof ApiError ? error.message : undefined)

  const save = useMutation({
    mutationFn: (body: Parameters<typeof adminApi.updateItem>[2]) =>
      adminApi.updateItem(shop.id, item.id, body),
    onSuccess: () => {
      setEditing(false)
      toast.success(t('adminProducts.saved'))
      refresh()
    },
    onError: fail,
  })
  const photo = useMutation({
    mutationFn: (file: File) => adminApi.replaceItemImage(shop.id, item.id, file),
    onSuccess: () => {
      toast.success(t('adminProducts.photoReplaced'))
      refresh()
    },
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: () => adminApi.deleteItem(shop.id, item.id),
    onSuccess: () => {
      toast.success(t('adminProducts.deleted'))
      refresh()
    },
    onError: fail,
  })

  return (
    <Card>
      <CardBody className="space-y-3 p-4">
        <div className="flex flex-wrap items-start gap-4">
          <span className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-sand-100">
            {item.image_url ? (
              <img src={item.image_thumb_url ?? item.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />
            ) : (
              <span className="flex h-full items-center justify-center text-sand-500">
                <Package className="h-6 w-6" aria-hidden="true" />
              </span>
            )}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{item.title}</span>
              {price ? <span className="ltr-nums text-sm font-bold text-brand-800">{price}</span> : null}
              {!item.is_available ? (
                <Badge className="bg-ink-100 text-ink-700">{t('adminProducts.hidden')}</Badge>
              ) : null}
              {!item.image_url ? (
                <Badge className="bg-clay-50 text-clay-700">{t('adminProducts.noPhotoBadge')}</Badge>
              ) : null}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-500">
              <Link to={`/admin/businesses/${shop.id}`} className="text-brand-700 hover:underline">
                {shop.name}
              </Link>
              <StatusBadge status={shop.status} />
              <button type="button" className="text-xs underline" onClick={() => onShop(shop.id)}>
                {t('adminProducts.onlyThisShop')}
              </button>
              <span className="text-xs text-ink-300">
                {formatRelativeDate(row.created_at, locale, t)}
              </span>
            </div>
          </div>
          {canEdit ? (
            <div className="flex flex-wrap gap-1">
              <Button size="sm" variant="ghost" onClick={() => setEditing((open) => !open)} aria-expanded={editing}>
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {t('adminProducts.edit')}
              </Button>
              <Button size="sm" variant="ghost" loading={photo.isPending} onClick={() => fileRef.current?.click()}>
                <ImageUp className="h-4 w-4" aria-hidden="true" />
                {t('adminProducts.replacePhoto')}
              </Button>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) photo.mutate(file)
                  event.target.value = ''
                }}
              />
              <Button
                size="sm"
                variant="ghost"
                loading={save.isPending && !editing}
                onClick={() => save.mutate({ is_available: !item.is_available })}
              >
                {item.is_available ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
                {item.is_available ? t('adminProducts.hide') : t('adminProducts.show')}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-clay-600"
                loading={remove.isPending}
                onClick={() => {
                  if (window.confirm(t('adminProducts.deleteConfirm', { name: item.title }))) remove.mutate()
                }}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {t('adminProducts.delete')}
              </Button>
            </div>
          ) : null}
        </div>

        {editing ? (
          <EditForm row={row} pending={save.isPending} onSave={(body) => save.mutate(body)} onCancel={() => setEditing(false)} />
        ) : null}
      </CardBody>
    </Card>
  )
}

function EditForm({
  row,
  pending,
  onSave,
  onCancel,
}: {
  row: AdminItem
  pending: boolean
  onSave: (body: Parameters<typeof adminApi.updateItem>[2]) => void
  onCancel: () => void
}) {
  const { t } = useI18n()
  const { item } = row
  const [title, setTitle] = useState(item.title)
  const [description, setDescription] = useState(item.description ?? '')
  const [price, setPrice] = useState(item.price ?? '')
  const [origin, setOrigin] = useState<GoodsOrigin>(item.goods_origin)
  const id = item.id

  return (
    <form
      className="grid gap-3 rounded-xl bg-sand-50 p-3 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({
          title: title.trim(),
          description: description.trim() || null,
          price: price.trim() || null,
          goods_origin: origin,
        })
      }}
    >
      <div className="sm:col-span-2">
        <label htmlFor={`title-${id}`} className="mb-1 block text-sm font-semibold text-ink-700">
          {t('adminProducts.fieldTitle')}
        </label>
        <Input id={`title-${id}`} value={title} onChange={(event) => setTitle(event.target.value)} required />
      </div>
      <div className="sm:col-span-2">
        <label htmlFor={`description-${id}`} className="mb-1 block text-sm font-semibold text-ink-700">
          {t('adminProducts.fieldDescription')}
        </label>
        <Textarea
          id={`description-${id}`}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
        />
      </div>
      <div>
        <label htmlFor={`price-${id}`} className="mb-1 block text-sm font-semibold text-ink-700">
          {t('adminProducts.fieldPrice', { currency: item.currency })}
        </label>
        <Input
          id={`price-${id}`}
          inputMode="decimal"
          className="ltr-nums"
          value={price}
          onChange={(event) => setPrice(event.target.value)}
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold text-ink-700" id={`origin-${id}`}>
          {t('directory.origin')}
        </label>
        <Select value={origin} onValueChange={(value) => setOrigin(value as GoodsOrigin)}>
          <SelectTrigger aria-labelledby={`origin-${id}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="LOCAL">{t('directory.originLocal')}</SelectItem>
            <SelectItem value="IMPORTED">{t('onboarding.importedTitle')}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" size="sm" loading={pending} disabled={!title.trim()}>
          {t('adminProducts.save')}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
      </div>
    </form>
  )
}
