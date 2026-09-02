import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, Package, Pencil, Plus, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'
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
      toast.success('تم حذف العنصر')
      invalidate()
    },
    onError: (error) =>
      toast.error('تعذر الحذف', error instanceof ApiError ? error.message : undefined),
  })

  const uploadImage = useMutation({
    mutationFn: ({ itemId, file }: { itemId: string; file: File }) =>
      ownerApi.uploadItemImage(businessId, itemId, file),
    onSuccess: () => {
      toast.success('تم رفع صورة العنصر')
      invalidate()
    },
    onError: (error) =>
      toast.error('تعذر رفع الصورة', error instanceof ApiError ? error.message : undefined),
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
        <p className="text-ink-500">
          أضف المنتجات أو الخدمات أو أصناف القائمة مع أسعارها.
        </p>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          إضافة عنصر
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
          title="لا توجد عناصر بعد"
          description="أضف أول منتج أو خدمة ليراها الزوار على صفحتك."
          action={<Button onClick={openCreate}>إضافة عنصر</Button>}
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

  return (
    <Card className={item.is_available ? '' : 'opacity-70'}>
      <CardBody className="flex gap-4 p-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 border-dashed border-ink-100 bg-sand-50"
          aria-label={`رفع صورة لـ ${item.title}`}
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
              <span className="ltr-nums shrink-0 text-sm font-bold text-clay-700">
                {formatPrice(item.price, item.currency)}
              </span>
            ) : null}
          </div>
          {item.description ? (
            <p className="mt-1 line-clamp-2 text-sm text-ink-500">{item.description}</p>
          ) : null}
          {!item.is_available ? <p className="mt-1 text-xs text-ink-500">غير متوفر حالياً</p> : null}

          <div className="mt-2 flex gap-1">
            <Button variant="ghost" size="sm" onClick={onEdit}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              تعديل
            </Button>
            <Button variant="ghost" size="sm" className="text-clay-600" onClick={onDelete}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              حذف
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
  const isEdit = item !== null

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ItemValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      title: item?.title ?? '',
      description: item?.description ?? '',
      price: item?.price ?? '',
      currency: item?.currency ?? 'USD',
      is_available: item?.is_available ?? true,
    },
  })

  const save = useMutation({
    mutationFn: (values: ItemValues) => {
      const payload = {
        title: values.title,
        description: values.description || null,
        price: values.price ? values.price : null,
        currency: values.currency,
        is_available: values.is_available,
      }
      return isEdit
        ? ownerApi.updateItem(businessId, item.id, payload)
        : ownerApi.createItem(businessId, payload)
    },
    onSuccess: () => {
      toast.success(isEdit ? 'تم تحديث العنصر' : 'تمت إضافة العنصر')
      onDone()
    },
    onError: (error) =>
      toast.error('تعذر الحفظ', error instanceof ApiError ? error.message : undefined),
  })

  return (
    <DialogContent title={isEdit ? 'تعديل العنصر' : 'إضافة عنصر جديد'}>
      <form onSubmit={handleSubmit((values) => save.mutate(values))} className="space-y-4" noValidate>
        <Field label="الاسم" required error={errors.title?.message}>
          {(props) => (
            <Input {...props} {...register('title')} placeholder="مثال: منقوشة زعتر" invalid={Boolean(errors.title)} autoFocus />
          )}
        </Field>

        <Field label="الوصف" error={errors.description?.message}>
          {(props) => <Textarea {...props} {...register('description')} rows={3} />}
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="السعر" error={errors.price?.message}>
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

          <Field label="العملة" required error={errors.currency?.message}>
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
                      <SelectItem value="USD">دولار أميركي ($)</SelectItem>
                      <SelectItem value="LBP">ليرة لبنانية (ل.ل.)</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            )}
          </Field>
        </div>

        <label className="flex items-center gap-3 rounded-xl border-2 border-ink-100 p-3.5">
          <input type="checkbox" {...register('is_available')} className="h-5 w-5 accent-clay-500" />
          <span className="font-medium">متوفر حالياً</span>
        </label>

        <div className="flex gap-3 pt-2">
          <Button type="submit" block loading={save.isPending}>
            {isEdit ? 'حفظ التعديلات' : 'إضافة العنصر'}
          </Button>
        </div>
      </form>
    </DialogContent>
  )
}
