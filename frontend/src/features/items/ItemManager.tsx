import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, ImagePlus, Package, Pencil, Plus, Trash2 } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import { ApiError } from '@/services/api/client'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { BusinessItem } from '@/types/api'
import { formatPrice } from '@/utils/format'
import { itemSchema, type ItemValues } from '@/utils/validation'

/**
 * Products / services / menu items.
 *
 * One concept covers all three: a restaurant sees a menu, a shop sees products,
 * a tradesperson sees services.
 */
export function ItemManager({ businessId }: { businessId: string }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const t = useT()
  const [editing, setEditing] = useState<BusinessItem | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const items = useQuery({
    queryKey: queryKeys.myBusinessItems(businessId),
    queryFn: () => ownerApi.items(businessId),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinessItems(businessId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(businessId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const remove = useMutation({
    mutationFn: (itemId: string) => ownerApi.deleteItem(businessId, itemId),
    onSuccess: () => {
      toast.success(t('items.deleted'))
      invalidate()
    },
    onError: (error) =>
      toast.error(t('items.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const uploadImage = useMutation({
    mutationFn: ({ itemId, file }: { itemId: string; file: File }) =>
      ownerApi.uploadItemImage(businessId, itemId, file),
    onSuccess: () => {
      toast.success(t('items.imageUploaded'))
      invalidate()
    },
    onError: (error) =>
      toast.error(
        t('items.imageUploadFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }

  const openEdit = (item: BusinessItem) => {
    setEditing(item)
    setDialogOpen(true)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-ink-500">{t('items.intro')}</p>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('items.addItem')}
        </Button>
      </div>

      {items.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      ) : items.isError ? (
        <ErrorState error={items.error} onRetry={() => void items.refetch()} />
      ) : items.data && items.data.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {items.data.map((item) => (
            <li key={item.id}>
              <ItemRow
                item={item}
                onEdit={() => openEdit(item)}
                onDelete={() => remove.mutate(item.id)}
                onUploadImage={(file) => uploadImage.mutate({ itemId: item.id, file })}
                uploading={uploadImage.isPending && uploadImage.variables?.itemId === item.id}
              />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={<Package className="h-7 w-7" aria-hidden="true" />}
          title={t('items.emptyTitle')}
          description={t('items.emptyDescription')}
          action={<Button onClick={openCreate}>{t('items.addItem')}</Button>}
        />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        {dialogOpen ? (
          <ItemDialog
            businessId={businessId}
            item={editing}
            onDone={() => {
              setDialogOpen(false)
              invalidate()
            }}
          />
        ) : null}
      </Dialog>
    </div>
  )
}

function ItemRow({
  item,
  onEdit,
  onDelete,
  onUploadImage,
  uploading,
}: {
  item: BusinessItem
  onEdit: () => void
  onDelete: () => void
  onUploadImage: (file: File) => void
  uploading: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const t = useT()

  return (
    <Card className={item.is_available ? '' : 'opacity-70'}>
      <CardBody className="flex gap-4 p-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 border-dashed border-ink-100 bg-sand-50"
          aria-label={t('items.uploadImageAria', { title: item.title })}
        >
          {item.image_url ? (
            <img src={item.image_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <span className="flex h-full items-center justify-center text-ink-300">
              <ImagePlus className="h-6 w-6" aria-hidden="true" />
            </span>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          disabled={uploading}
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) onUploadImage(file)
            event.target.value = ''
          }}
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-bold">{item.title}</h4>
            {formatPrice(item.price, item.currency) ? (
              <span className="ltr-nums shrink-0 text-sm font-bold text-brand-800">
                {formatPrice(item.price, item.currency)}
              </span>
            ) : null}
          </div>
          {item.description ? (
            <p className="mt-1 line-clamp-2 text-sm text-ink-500">{item.description}</p>
          ) : null}
          {!item.is_available ? (
            <p className="mt-1 text-xs text-ink-500">{t('items.unavailable')}</p>
          ) : null}

          <div className="mt-2 flex gap-1">
            <Button variant="ghost" size="sm" onClick={onEdit}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {t('common.edit')}
            </Button>
            <Button variant="ghost" size="sm" className="text-clay-600" onClick={onDelete}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('common.delete')}
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

function ItemDialog({
  businessId,
  item,
  onDone,
}: {
  businessId: string
  item: BusinessItem | null
  onDone: () => void
}) {
  const toast = useToast()
  const t = useT()
  const isEdit = item !== null
  const schema = useMemo(() => itemSchema(t), [t])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(item?.image_url ?? null)

  const {
    register,
    handleSubmit,
    control,
    setError,
    getValues,
    formState: { errors },
  } = useForm<ItemValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: item?.title ?? '',
      description: item?.description ?? '',
      price: item?.price ?? '',
      currency: item?.currency ?? 'USD',
      is_available: item?.is_available ?? true,
      good_type: item?.good_type ?? '',
      brand_name: item?.brand_name ?? '',
      ingredients: item?.ingredients ?? '',
      manufactured_at: item?.manufactured_at ?? '',
      expiry_date: item?.expiry_date ?? '',
      net_weight: item?.net_weight ?? '',
      external_link: item?.external_link ?? '',
    },
  })

  const pickFile = (file: File) => {
    setSelectedFile(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  // One save covers both: the fields and, if a photo was picked, the image —
  // a new item has no id to attach a photo to until it exists, so the image
  // upload (when there is one) always runs right after the create/update
  // resolves, as a single submit rather than "save, then separately go find
  // the small thumbnail to add a photo."
  const save = useMutation({
    mutationFn: async (values: ItemValues) => {
      const payload = {
        title: values.title,
        description: values.description || null,
        price: values.price ? values.price : null,
        currency: values.currency,
        is_available: values.is_available,
        good_type: values.good_type || null,
        brand_name: values.brand_name || null,
        ingredients: values.ingredients || null,
        manufactured_at: values.manufactured_at || null,
        expiry_date: values.expiry_date || null,
        net_weight: values.net_weight || null,
        external_link: values.external_link || null,
      }
      const saved = isEdit
        ? await ownerApi.updateItem(businessId, item.id, payload)
        : await ownerApi.createItem(businessId, payload)
      if (selectedFile) {
        return ownerApi.uploadItemImage(businessId, saved.id, selectedFile)
      }
      return saved
    },
    onSuccess: () => {
      toast.success(isEdit ? t('items.updated') : t('items.created'))
      onDone()
    },
    onError: (error) =>
      toast.error(t('items.saveFailed'), error instanceof ApiError ? error.message : undefined),
  })

  useApplyServerFieldErrors(save.error, setError, getValues)

  return (
    <DialogContent title={isEdit ? t('items.dialogEdit') : t('items.dialogAdd')}>
      <form onSubmit={handleSubmit((values) => save.mutate(values))} className="space-y-4" noValidate>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 border-dashed border-ink-100 bg-sand-50"
          >
            {previewUrl ? (
              <img src={previewUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              <span className="flex h-full items-center justify-center text-ink-300">
                <ImagePlus className="h-6 w-6" aria-hidden="true" />
              </span>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) pickFile(file)
              event.target.value = ''
            }}
          />
          <div>
            <p className="text-sm font-semibold">{t('items.photoLabel')}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
              {previewUrl ? t('items.photoChange') : t('items.photoChoose')}
            </Button>
          </div>
        </div>

        <Field label={t('items.nameLabel')} required error={errors.title?.message}>
          {(props) => (
            <Input {...props} {...register('title')} placeholder={t('items.namePlaceholder')} invalid={Boolean(errors.title)} autoFocus />
          )}
        </Field>

        <Field label={t('items.descriptionLabel')} error={errors.description?.message}>
          {(props) => <Textarea {...props} {...register('description')} rows={3} />}
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label={t('items.priceLabel')} error={errors.price?.message}>
            {(props) => (
              <Input
                {...props}
                {...register('price')}
                inputMode="decimal"
                dir="ltr"
                placeholder="1.50"
                className="ltr-nums"
                invalid={Boolean(errors.price)}
              />
            )}
          </Field>

          <Field label={t('items.currencyLabel')} required error={errors.currency?.message}>
            {(props) => (
              <Controller
                control={control}
                name="currency"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id={props.id}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">{t('items.currencyUsd')}</SelectItem>
                      <SelectItem value="LBP">{t('items.currencyLbp')}</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            )}
          </Field>
        </div>

        <label className="flex items-center gap-3 rounded-xl border-2 border-ink-100 p-3.5">
          <input type="checkbox" {...register('is_available')} className="h-5 w-5 accent-brand-600" />
          <span className="font-medium">{t('items.availableLabel')}</span>
        </label>

        <fieldset className="space-y-4 rounded-xl border-2 border-ink-100 p-3.5">
          <legend className="px-1 text-sm font-semibold">{t('items.goodDetailHeading')}</legend>
          <p className="text-xs text-ink-500">{t('items.goodDetailHint')}</p>

          <div className="grid grid-cols-2 gap-4">
            <Field label={t('items.goodTypeLabel')} error={errors.good_type?.message}>
              {(props) => <Input {...props} {...register('good_type')} invalid={Boolean(errors.good_type)} />}
            </Field>
            <Field label={t('items.brandNameLabel')} error={errors.brand_name?.message}>
              {(props) => <Input {...props} {...register('brand_name')} invalid={Boolean(errors.brand_name)} />}
            </Field>
          </div>

          <Field label={t('items.ingredientsLabel')} error={errors.ingredients?.message}>
            {(props) => <Textarea {...props} {...register('ingredients')} rows={2} />}
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label={t('items.manufacturedAtLabel')} error={errors.manufactured_at?.message}>
              {(props) => (
                <Input
                  {...props}
                  {...register('manufactured_at')}
                  type="date"
                  dir="ltr"
                  className="ltr-nums"
                  invalid={Boolean(errors.manufactured_at)}
                />
              )}
            </Field>
            <Field label={t('items.expiryDateLabel')} error={errors.expiry_date?.message}>
              {(props) => (
                <Input
                  {...props}
                  {...register('expiry_date')}
                  type="date"
                  dir="ltr"
                  className="ltr-nums"
                  invalid={Boolean(errors.expiry_date)}
                />
              )}
            </Field>
          </div>

          <Field label={t('items.netWeightLabel')} error={errors.net_weight?.message}>
            {(props) => <Input {...props} {...register('net_weight')} invalid={Boolean(errors.net_weight)} />}
          </Field>

          <Field label={t('items.externalLinkLabel')} error={errors.external_link?.message}>
            {(props) => (
              <Input
                {...props}
                {...register('external_link')}
                dir="ltr"
                placeholder="https://"
                invalid={Boolean(errors.external_link)}
              />
            )}
          </Field>
        </fieldset>

        {isEdit ? <ItemGalleryManager businessId={businessId} item={item} /> : null}

        <div className="flex gap-3 pt-2">
          <Button type="submit" block loading={save.isPending}>
            {isEdit ? t('items.saveAction') : t('items.addAction')}
          </Button>
        </div>
      </form>
    </DialogContent>
  )
}

function ItemGalleryManager({ businessId, item }: { businessId: string; item: BusinessItem }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const t = useT()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinessItems(businessId) })
  }

  const upload = useMutation({
    mutationFn: (file: File) => ownerApi.uploadItemGalleryImage(businessId, item.id, file),
    onSuccess: invalidate,
    onError: (error) =>
      toast.error(t('items.imageUploadFailed'), error instanceof ApiError ? error.message : undefined),
    onSettled: () => setUploading(false),
  })

  const remove = useMutation({
    mutationFn: (imageId: string) => ownerApi.deleteItemGalleryImage(businessId, item.id, imageId),
    onSuccess: invalidate,
  })

  const reorder = useMutation({
    mutationFn: (imageIds: string[]) => ownerApi.reorderItemGalleryImages(businessId, item.id, imageIds),
    onSuccess: invalidate,
  })

  const move = (index: number, direction: -1 | 1) => {
    const next = [...item.images]
    const target = index + direction
    const moved = next[index]
    const swapped = next[target]
    if (!moved || !swapped) return
    next[index] = swapped
    next[target] = moved
    reorder.mutate(next.map((image) => image.id))
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">{t('items.galleryHeading')}</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) {
              setUploading(true)
              upload.mutate(file)
            }
            event.target.value = ''
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          <ImagePlus className="h-4 w-4" aria-hidden="true" />
          {t('items.galleryAdd')}
        </Button>
      </div>

      {item.images.length === 0 ? (
        <p className="rounded-xl border-2 border-dashed border-ink-100 p-4 text-center text-sm text-ink-500">
          {t('items.galleryEmpty')}
        </p>
      ) : (
        <ul className="grid grid-cols-3 gap-2">
          {item.images.map((image, index) => (
            <li key={image.id} className="group relative overflow-hidden rounded-xl border border-ink-100 bg-sand-100">
              <img src={image.url} alt={image.caption ?? ''} className="h-20 w-full object-cover" />
              <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-ink-900/60 p-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => move(index, -1)}
                    disabled={index === 0 || reorder.isPending}
                    className="rounded bg-white/90 p-1 text-ink-900 disabled:opacity-40"
                    aria-label={t('images.moveBack')}
                  >
                    <ArrowRight className="h-3 w-3" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(index, 1)}
                    disabled={index === item.images.length - 1 || reorder.isPending}
                    className="rounded bg-white/90 p-1 text-ink-900 disabled:opacity-40"
                    aria-label={t('images.moveForward')}
                  >
                    <ArrowLeft className="h-3 w-3" aria-hidden="true" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => remove.mutate(image.id)}
                  className="rounded bg-clay-600 p-1 text-white"
                  aria-label={t('images.deleteImage')}
                >
                  <Trash2 className="h-3 w-3" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
