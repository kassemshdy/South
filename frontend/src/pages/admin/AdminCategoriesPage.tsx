import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Category } from '@/types/api'

export function AdminCategoriesPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

  const categories = useQuery({ queryKey: queryKeys.adminCategories, queryFn: adminApi.categories })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminCategories })
    void queryClient.invalidateQueries({ queryKey: queryKeys.categories })
  }

  const handleError = (error: unknown, fallback: string) =>
    toast.error(fallback, error instanceof ApiError ? error.message : undefined)

  const create = useMutation({
    mutationFn: (name_ar: string) => adminApi.createCategory({ name_ar }),
    onSuccess: () => {
      setNewName('')
      toast.success('تمت إضافة التصنيف')
      invalidate()
    },
    onError: (error) => handleError(error, 'تعذر إضافة التصنيف'),
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Category> }) => adminApi.updateCategory(id, body),
    onSuccess: () => {
      setEditingId(null)
      toast.success('تم حفظ التصنيف')
      invalidate()
    },
    onError: (error) => handleError(error, 'تعذر حفظ التصنيف'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteCategory(id),
    onSuccess: () => {
      toast.success('تم حذف التصنيف')
      invalidate()
    },
    onError: (error) => handleError(error, 'تعذر حذف التصنيف'),
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">التصنيفات</h1>
        <p className="mt-2 text-ink-500">
          التصنيفات تُحمَّل من قاعدة البيانات وتظهر مباشرة للزوار.
        </p>
      </header>

      <Card>
        <CardBody>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (newName.trim().length >= 2) create.mutate(newName.trim())
            }}
            className="flex gap-2"
          >
            <label htmlFor="new-category" className="sr-only">
              اسم التصنيف الجديد
            </label>
            <Input
              id="new-category"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder="اسم التصنيف الجديد"
            />
            <Button type="submit" loading={create.isPending} disabled={newName.trim().length < 2}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              إضافة
            </Button>
          </form>
        </CardBody>
      </Card>

      {categories.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : categories.isError ? (
        <ErrorState error={categories.error} onRetry={() => void categories.refetch()} />
      ) : (
        <ul className="space-y-2">
          {categories.data?.map((category) => (
            <li key={category.id}>
              <Card>
                <CardBody className="flex flex-wrap items-center justify-between gap-3 p-4">
                  {editingId === category.id ? (
                    <form
                      onSubmit={(event) => {
                        event.preventDefault()
                        update.mutate({ id: category.id, body: { name_ar: editingName } })
                      }}
                      className="flex flex-1 gap-2"
                    >
                      <Input value={editingName} onChange={(event) => setEditingName(event.target.value)} autoFocus />
                      <Button type="submit" size="icon" loading={update.isPending} aria-label="حفظ">
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button type="button" size="icon" variant="ghost" onClick={() => setEditingId(null)} aria-label="إلغاء">
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">{category.name_ar}</span>
                        <span className="ltr-nums text-xs text-ink-300">{category.slug}</span>
                        {!category.is_active ? <Badge className="bg-ink-100 text-ink-700">غير مفعّل</Badge> : null}
                      </div>

                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            update.mutate({ id: category.id, body: { is_active: !category.is_active } })
                          }
                        >
                          {category.is_active ? 'إلغاء التفعيل' : 'تفعيل'}
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditingId(category.id)
                            setEditingName(category.name_ar)
                          }}
                          aria-label={`تعديل ${category.name_ar}`}
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-clay-600"
                          onClick={() => remove.mutate(category.id)}
                          aria-label={`حذف ${category.name_ar}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </>
                  )}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
