import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { useToast } from '@/components/ui/Toast'
import { ProductCategorySelect } from '@/features/items/ProductCategorySelect'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import type { ProductSummary } from '@/types/api'

/**
 * Staff change a product's category from the catalogue itself (the owners'
 * ticket, 16 Nov 2026), without opening the admin panel. Saved on pick;
 * the shop's other products and the shop's own category stay as they are.
 */
export function StaffProductCategory({ product }: { product: ProductSummary }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [value, setValue] = useState(product.category?.id ?? '')
  const labelId = `staff-category-${product.id}`
  const save = useMutation({
    mutationFn: (categoryId: string) =>
      adminApi.updateItem(product.business.id, product.id, { category_id: categoryId }),
    onSuccess: () => {
      toast.success(t('adminProducts.saved'))
      void queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (error) => {
      setValue(product.category?.id ?? '')
      toast.error(t('states.errorFallback'), error instanceof ApiError ? error.message : undefined)
    },
  })
  return (
    <div className="mt-3 rounded-xl border border-dashed border-ink-100 p-2">
      <span id={labelId} className="mb-1 block text-xs font-semibold text-ink-500">
        {t('items.staffCategoryLabel')}
      </span>
      <ProductCategorySelect
        labelledBy={labelId}
        value={value}
        disabled={save.isPending}
        onChange={(next) => {
          setValue(next)
          save.mutate(next)
        }}
      />
    </div>
  )
}
