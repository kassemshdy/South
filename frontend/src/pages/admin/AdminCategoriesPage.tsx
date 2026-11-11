import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Combine, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
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
  // The category being merged, and the one it goes into.
  const [mergingId, setMergingId] = useState<string | null>(null)
  const [mergeInto, setMergeInto] = useState('')
  const t = useT()

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
      toast.success(t('admin.categoryAdded'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.categoryAddFailed')),
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Category> }) => adminApi.updateCategory(id, body),
    onSuccess: () => {
      setEditingId(null)
      toast.success(t('admin.categorySaved'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.categorySaveFailed')),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteCategory(id),
    onSuccess: () => {
      toast.success(t('admin.categoryDeleted'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.categoryDeleteFailed')),
  })

  // Folding one category into another (the owners' request, 11 Nov 2026):
  // a category with shops cannot be deleted, so this is how one goes.
  const merge = useMutation({
    mutationFn: ({ id, into }: { id: string; into: string }) => adminApi.mergeCategory(id, into),
    onSuccess: (result) => {
      setMergingId(null)
      setMergeInto('')
      toast.success(result.message)
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.categoryMergeFailed')),
  })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.categoriesHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.categoriesSubtitle')}</p>
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
              {t('admin.newCategoryLabel')}
            </label>
            <Input
              id="new-category"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder={t('admin.newCategoryLabel')}
            />
            <Button type="submit" loading={create.isPending} disabled={newName.trim().length < 2}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('admin.add')}
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
                      <Button type="submit" size="icon" loading={update.isPending} aria-label={t('admin.saveAria')}>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button type="button" size="icon" variant="ghost" onClick={() => setEditingId(null)} aria-label={t('admin.cancelAria')}>
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">{category.name_ar}</span>
                        <span className="ltr-nums text-xs text-ink-300">{category.slug}</span>
                        <span className="text-xs text-ink-500">
                          {t('admin.categoryShopCount', { count: category.business_count })}
                        </span>
                        {!category.is_active ? (
                          <Badge className="bg-ink-100 text-ink-700">
                            {t('common.inactive')}
                          </Badge>
                        ) : null}
                      </div>

                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            update.mutate({ id: category.id, body: { is_active: !category.is_active } })
                          }
                        >
                          {category.is_active ? t('common.deactivate') : t('common.activate')}
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditingId(category.id)
                            setEditingName(category.name_ar)
                          }}
                          aria-label={t('admin.editAria', { name: category.name_ar })}
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setMergingId(mergingId === category.id ? null : category.id)
                            setMergeInto('')
                          }}
                          aria-expanded={mergingId === category.id}
                        >
                          <Combine className="h-4 w-4" aria-hidden="true" />
                          {t('admin.categoryMerge')}
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-clay-600"
                          onClick={() => remove.mutate(category.id)}
                          aria-label={t('admin.deleteAria', { name: category.name_ar })}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                      {mergingId === category.id ? (
                        <div className="flex w-full flex-wrap items-end gap-2 rounded-xl bg-sand-50 p-3">
                          <div className="min-w-56 flex-1">
                            <label className="mb-1 block text-sm font-semibold text-ink-700" id={`merge-${category.id}`}>
                              {t('admin.categoryMergeInto', { name: category.name_ar })}
                            </label>
                            <Select value={mergeInto} onValueChange={setMergeInto}>
                              <SelectTrigger aria-labelledby={`merge-${category.id}`}>
                                <SelectValue placeholder={t('admin.categoryMergePick')} />
                              </SelectTrigger>
                              <SelectContent>
                                {(categories.data ?? [])
                                  .filter((other) => other.id !== category.id)
                                  .map((other) => (
                                    <SelectItem key={other.id} value={other.id}>
                                      {other.name_ar}
                                    </SelectItem>
                                  ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <Button
                            size="sm"
                            disabled={!mergeInto}
                            loading={merge.isPending}
                            onClick={() => merge.mutate({ id: category.id, into: mergeInto })}
                          >
                            {t('admin.categoryMergeConfirm', { count: category.business_count })}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setMergingId(null)}>
                            {t('common.cancel')}
                          </Button>
                        </div>
                      ) : null}
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
