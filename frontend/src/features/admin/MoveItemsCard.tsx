import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminBusiness } from '@/types/api'

/**
 * Every product of this listing, to another listing of the same owner: for
 * an owner who filled a second, never-submitted shop instead of the approved
 * one (the owners' report, 7 Nov 2026). Two steps, like replacing a password:
 * pick the shop, then confirm. Nothing when the owner has no other listing.
 */
export function MoveItemsCard({ business }: { business: AdminBusiness }) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [target, setTarget] = useState<AdminBusiness | null>(null)
  const owner = useQuery({
    queryKey: queryKeys.adminUser(business.owner_id),
    queryFn: () => adminApi.user(business.owner_id),
  })
  const move = useMutation({
    mutationFn: (to: AdminBusiness) => adminApi.moveItems(business.id, to.id),
    onSuccess: (moved) => {
      void queryClient.invalidateQueries({ queryKey: ['admin'] })
      toast.success(t('admin.moveItemsDone', { count: moved.items.length, name: moved.name }))
      navigate(`/admin/businesses/${moved.id}`)
    },
    onError: (error) =>
      toast.error(t('admin.moveItemsFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const others = (owner.data?.businesses ?? []).filter((shop) => shop.id !== business.id)
  if (business.items.length === 0 || others.length === 0) return null

  return (
    <Card>
      <CardBody className="space-y-3">
        <h2 className="font-bold">{t('admin.moveItemsTitle')}</h2>
        <p className="text-sm text-ink-500">
          {t('admin.moveItemsHint', { count: business.items.length })}
        </p>
        {target ? (
          <div className="space-y-3 rounded-xl border border-clay-200 bg-clay-50 p-3.5">
            <p className="text-sm text-clay-800">
              {t('admin.moveItemsConfirm', { count: business.items.length, name: target.name })}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" loading={move.isPending} onClick={() => move.mutate(target)}>
                {t('common.confirm')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setTarget(null)}>
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        ) : (
          <ul className="space-y-2">
            {others.map((shop) => (
              <li key={shop.id}>
                <Button variant="outline" size="sm" onClick={() => setTarget(shop)}>
                  <ArrowLeftRight className="h-4 w-4" aria-hidden="true" />
                  <span dir="auto">{t('admin.moveItemsTo', { name: shop.name })}</span>
                  <StatusBadge status={shop.status} />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}
