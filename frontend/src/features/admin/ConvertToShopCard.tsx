import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Store } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, taxonomyApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * A seller who applied as a service but sells goods: move the profile into
 * a shop for the same owner (see `TalentConversionService`). The service
 * profile is removed, so it asks first, then opens the new shop.
 */
export function ConvertToShopCard({ profileId }: { profileId: string }) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: taxonomyApi.categories })
  const [categoryId, setCategoryId] = useState('')

  const convert = useMutation({
    mutationFn: () => adminApi.convertTalentToBusiness(profileId, categoryId),
    onSuccess: ({ business_id }) => {
      void queryClient.invalidateQueries({ queryKey: ['admin'] })
      toast.success(t('admin.correctionSaved'))
      navigate(`/admin/businesses/${business_id}`)
    },
    onError: (error) =>
      toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <Card>
      <CardHeader>
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Store className="size-5 text-brand-700" aria-hidden />
          {t('admin.convertTitle')}
        </h2>
      </CardHeader>
      <CardBody className="space-y-3">
        <p className="text-sm text-ink-500">{t('admin.convertHint')}</p>
        <label className="block text-sm font-semibold" htmlFor="admin-convert-category">
          {t('form.category')}
        </label>
        <Select value={categoryId || undefined} onValueChange={setCategoryId}>
          <SelectTrigger id="admin-convert-category">
            <SelectValue placeholder={t('form.categoryPlaceholder')} />
          </SelectTrigger>
          <SelectContent>
            {categories.data?.map((category) => (
              <SelectItem key={category.id} value={category.id}>
                {category.name_ar}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          disabled={!categoryId}
          loading={convert.isPending}
          onClick={() => {
            if (window.confirm(t('admin.convertConfirm'))) convert.mutate()
          }}
        >
          {t('admin.convertButton')}
        </Button>
      </CardBody>
    </Card>
  )
}
