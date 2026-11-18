import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Sprout } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { GROWTH_STAGE_KEYS } from '@/features/growthProgramme/labels'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * On a shop's admin page: whether it is in the growth programme, at which
 * step, and a button to add it (the owners' decision, 18 Nov 2026).
 */
export function GrowthCard({ businessId }: { businessId: string }) {
  const { t } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('moderate')
  const row = useQuery({
    queryKey: queryKeys.adminGrowthProgrammeOf(businessId),
    queryFn: () => adminApi.growthProgrammeOf(businessId),
    retry: false,
  })
  const enrolled = row.isSuccess
  const enroll = useMutation({
    mutationFn: () => adminApi.growthProgrammeEnroll(businessId),
    onSuccess: (next) => {
      queryClient.setQueryData(queryKeys.adminGrowthProgrammeOf(businessId), next)
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminGrowthProgramme })
      toast.success(t('growthProgramme.added'))
    },
    onError: (error) =>
      toast.error(t('states.errorFallback'), error instanceof ApiError ? error.message : undefined),
  })
  if (row.isLoading) return null
  if (!enrolled && !canEdit) return null
  return (
    <Card>
      <CardBody className="space-y-2">
        <h2 className="flex items-center gap-2 font-bold">
          <Sprout className="h-5 w-5 text-olive-700" aria-hidden="true" />
          {t('growthProgramme.title')}
        </h2>
        {enrolled ? (
          <p className="text-sm text-ink-700">
            {t('growthProgramme.inProgramme', { stage: t(GROWTH_STAGE_KEYS[row.data.stage]) })}{' '}
            <Link to="/admin/growth-programme" className="font-semibold text-brand-700 hover:underline">
              {t('growthProgramme.open')}
            </Link>
          </p>
        ) : (
          <>
            <p className="text-sm text-ink-500">{t('growthProgramme.notIn')}</p>
            <Button size="sm" onClick={() => enroll.mutate()} loading={enroll.isPending}>
              {t('growthProgramme.add')}
            </Button>
          </>
        )}
      </CardBody>
    </Card>
  )
}
