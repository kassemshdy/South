import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MapPinOff, Wand2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { StrayPin } from '@/types/api'

/**
 * Map locations a person should look at, on a page of their own rather than
 * the dashboard (the owners' request, 9 Nov 2026):
 * - outside Lebanon -- saved before locations were checked, shown on no
 *   public map; one button moves every one that has a suggestion;
 * - inside it but far from the rest of their district -- often a displaced
 *   owner who set where they live now, so each is moved only on its own.
 * A suggestion is the middle of the other locations in the same town, or of
 * the district when the town has none.
 */
export function AdminMapLocationsPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canFix = useStaffCan('moderate')
  const pins = useQuery({ queryKey: queryKeys.adminStrayPins, queryFn: adminApi.strayPins })

  const apply = useMutation({
    mutationFn: (ids: string[]) => adminApi.applyStrayPins(ids),
    onSuccess: (result) => {
      toast.success(t('adminMapPins.applied', { moved: result.moved, skipped: result.skipped }))
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminStrayPins })
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const outside = pins.data?.filter((pin) => pin.reason === 'outside') ?? []
  const far = pins.data?.filter((pin) => pin.reason === 'far') ?? []
  const fixable = outside.filter((pin) => pin.suggested_latitude != null)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-3xl">
          <MapPinOff className="h-7 w-7 text-clay-600" aria-hidden="true" />
          {t('admin.strayPinsTitle')}
        </h1>
        <p className="mt-1 max-w-2xl text-ink-500">{t('adminMapPins.subtitle')}</p>
      </div>

      {pins.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : pins.isError ? (
        <ErrorState error={pins.error} onRetry={() => void pins.refetch()} />
      ) : !pins.data?.length ? (
        <EmptyState
          icon={<MapPinOff className="h-7 w-7" aria-hidden="true" />}
          title={t('adminMapPins.empty')}
        />
      ) : (
        <>
          {outside.length > 0 ? (
            <Card>
              <CardBody className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-bold">
                      {t('admin.strayPinsHeading', { count: outside.length })}
                    </h2>
                    <p className="mt-1 text-sm text-ink-500">{t('admin.strayPinsHint')}</p>
                  </div>
                  {canFix && fixable.length > 0 ? (
                    <Button
                      loading={apply.isPending}
                      onClick={() => {
                        if (window.confirm(t('adminMapPins.fixAllConfirm', { count: fixable.length })))
                          apply.mutate(fixable.map((pin) => pin.id))
                      }}
                    >
                      <Wand2 className="h-4 w-4" aria-hidden="true" />
                      {t('adminMapPins.fixAll', { count: fixable.length })}
                    </Button>
                  ) : null}
                </div>
                <PinList pins={outside} canFix={canFix} onApply={(id) => apply.mutate([id])} busy={apply.isPending} />
              </CardBody>
            </Card>
          ) : null}

          {far.length > 0 ? (
            <Card>
              <CardBody className="space-y-3">
                <div>
                  <h2 className="text-xl font-bold">
                    {t('admin.farPinsHeading', { count: far.length })}
                  </h2>
                  <p className="mt-1 text-sm text-ink-500">{t('admin.farPinsHint')}</p>
                </div>
                <PinList pins={far} canFix={canFix} onApply={(id) => apply.mutate([id])} busy={apply.isPending} />
              </CardBody>
            </Card>
          ) : null}
        </>
      )}
    </div>
  )
}

function PinList({
  pins,
  canFix,
  onApply,
  busy,
}: {
  pins: StrayPin[]
  canFix: boolean
  onApply: (id: string) => void
  busy: boolean
}) {
  const t = useT()
  return (
    <ul className="divide-y divide-ink-100 rounded-xl border border-ink-100">
      {pins.map((pin) => (
        <li key={pin.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <Link
              to={pin.kind === 'business' ? `/admin/businesses/${pin.id}` : `/admin/talent/${pin.id}`}
              className="font-semibold hover:text-brand-700"
              dir="auto"
            >
              {pin.name}
            </Link>
            <p className="ltr-nums text-sm text-ink-500">
              {[
                t(pin.kind === 'business' ? 'admin.strayPinShop' : 'admin.strayPinService'),
                pin.town,
                pin.km_from_district != null
                  ? t('admin.farPinKm', { count: pin.km_from_district })
                  : null,
                pin.published ? null : t('adminMapPins.notPublished'),
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
            <p className="text-xs text-ink-400">
              {pin.suggested_from
                ? t(pin.suggested_from === 'town' ? 'adminMapPins.suggestTown' : 'adminMapPins.suggestDistrict')
                : t('adminMapPins.noSuggestion')}
            </p>
          </div>
          {canFix && pin.suggested_latitude != null ? (
            <Button variant="outline" size="sm" disabled={busy} onClick={() => onApply(pin.id)}>
              {t('adminMapPins.apply')}
            </Button>
          ) : null}
        </li>
      ))}
    </ul>
  )
}
