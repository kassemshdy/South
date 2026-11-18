import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Sprout, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { GROWTH_STAGE_KEYS, change } from '@/features/growthProgramme/labels'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { GROWTH_STAGES, type GrowthRow, type GrowthStage } from '@/types/api'
import { formatDate } from '@/utils/format'

/**
 * The growth programme (the owners' decision, 18 Nov 2026): about fifty
 * serious shops taken through the same steps -- contact, content, listing,
 * Shopify, ads -- with their numbers on the day they joined beside today's.
 * Shops are added from their own admin page.
 */
export function AdminGrowthProgrammePage() {
  const { t } = useI18n()
  const [stage, setStage] = useState<GrowthStage | 'ALL'>('ALL')
  const rows = useQuery({ queryKey: queryKeys.adminGrowthProgramme, queryFn: adminApi.growthProgramme })
  const all = rows.data ?? []
  const counts = Object.fromEntries(
    GROWTH_STAGES.map((value) => [value, all.filter((row) => row.stage === value).length]),
  ) as Record<GrowthStage, number>
  const shown = stage === 'ALL' ? all : all.filter((row) => row.stage === stage)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Sprout className="h-6 w-6 text-olive-700" aria-hidden="true" />
          {t('growthProgramme.title')}
        </h1>
        <p className="mt-1 text-sm text-ink-500">{t('growthProgramme.intro', { count: all.length })}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={stage === 'ALL' ? 'primary' : 'outline'} onClick={() => setStage('ALL')}>
          {t('growthProgramme.all', { count: all.length })}
        </Button>
        {GROWTH_STAGES.map((value, index) => (
          <Button
            key={value}
            size="sm"
            variant={stage === value ? 'primary' : 'outline'}
            onClick={() => setStage(value)}
          >
            {index + 1}. {t(GROWTH_STAGE_KEYS[value])} ({counts[value]})
          </Button>
        ))}
      </div>

      {rows.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : rows.isError ? (
        <ErrorState error={rows.error} onRetry={() => void rows.refetch()} />
      ) : shown.length === 0 ? (
        <EmptyState title={t('growthProgramme.empty')} />
      ) : (
        <ul className="space-y-3">
          {shown.map((row) => (
            <GrowthItem key={row.shop.id} row={row} />
          ))}
        </ul>
      )}
    </div>
  )
}

function GrowthItem({ row }: { row: GrowthRow }) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('moderate')
  const [note, setNote] = useState(row.note ?? '')
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.adminGrowthProgramme })
  const fail = (error: unknown) =>
    toast.error(t('states.errorFallback'), error instanceof ApiError ? error.message : undefined)
  const update = useMutation({
    mutationFn: (body: { stage?: GrowthStage; note?: string | null }) =>
      adminApi.growthProgrammeUpdate(row.shop.id, body),
    onSuccess: () => {
      toast.success(t('growthProgramme.saved'))
      refresh()
    },
    onError: fail,
  })
  const leave = useMutation({
    mutationFn: () => adminApi.growthProgrammeLeave(row.shop.id),
    onSuccess: refresh,
    onError: fail,
  })
  const shop = row.shop

  return (
    <li>
      <Card>
        <CardBody className="space-y-3 p-4">
          <div className="flex flex-wrap items-start gap-3">
            <span className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-sand-100">
              {shop.logo_thumb_url ? (
                <img src={shop.logo_thumb_url} alt="" className="h-full w-full object-cover" />
              ) : null}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/admin/businesses/${shop.id}`} className="font-semibold text-brand-700 hover:underline">
                  {shop.name}
                </Link>
                <a
                  href={`/business/${encodeURIComponent(shop.slug)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ink-500 hover:text-brand-700"
                  aria-label={t('growthProgramme.publicPage')}
                >
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                </a>
                {shop.shopify_connected ? (
                  <Badge className="bg-olive-50 text-olive-800">{t('growthProgramme.shopifyConnected')}</Badge>
                ) : null}
              </div>
              <p className="text-sm text-ink-500">
                {[shop.category, shop.location].filter(Boolean).join(' · ')} ·{' '}
                {t('growthProgramme.products', { count: shop.products })}
              </p>
              <p className="text-xs text-ink-300">
                {t('growthProgramme.joined', {
                  date: formatDate(row.enrolled_at, locale),
                  name: row.enrolled_by_name ?? '—',
                })}
              </p>
            </div>
            {canEdit ? (
              <select
                aria-label={t('growthProgramme.stageLabel')}
                className="rounded-xl border border-ink-100 bg-white px-3 py-2 text-sm"
                value={row.stage}
                disabled={update.isPending}
                onChange={(event) => update.mutate({ stage: event.target.value as GrowthStage })}
              >
                {GROWTH_STAGES.map((value, index) => (
                  <option key={value} value={value}>
                    {index + 1}. {t(GROWTH_STAGE_KEYS[value])}
                  </option>
                ))}
              </select>
            ) : (
              <Badge>{t(GROWTH_STAGE_KEYS[row.stage])}</Badge>
            )}
          </div>

          <dl className="grid gap-2 text-sm sm:grid-cols-4">
            {(
              [
                ['growthProgramme.instagram', row.before.instagram, row.now.instagram],
                ['growthProgramme.facebook', row.before.facebook, row.now.facebook],
                ['growthProgramme.views', row.before.views_30d, row.now.views_30d],
                ['growthProgramme.clicks', row.before.clicks_30d, row.now.clicks_30d],
              ] as const
            ).map(([key, before, now]) => (
              <div key={key} className="rounded-xl bg-sand-50 px-3 py-2">
                <dt className="text-xs text-ink-500">{t(key)}</dt>
                <dd className="ltr-nums font-semibold text-ink-900" dir="ltr">
                  {change(before, now, locale)}
                </dd>
              </div>
            ))}
          </dl>

          {canEdit ? (
            <div className="flex flex-wrap items-end gap-2">
              <Textarea
                aria-label={t('growthProgramme.noteLabel')}
                placeholder={t('growthProgramme.noteLabel')}
                value={note}
                rows={2}
                className="min-w-0 flex-1"
                onChange={(event) => setNote(event.target.value)}
              />
              <Button
                size="sm"
                variant="outline"
                disabled={note === (row.note ?? '')}
                loading={update.isPending}
                onClick={() => update.mutate({ note: note.trim() || null })}
              >
                {t('growthProgramme.saveNote')}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                loading={leave.isPending}
                onClick={() => {
                  if (window.confirm(t('growthProgramme.removeConfirm', { name: shop.name }))) leave.mutate()
                }}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {t('growthProgramme.remove')}
              </Button>
            </div>
          ) : row.note ? (
            <p className="text-sm text-ink-700" dir="auto">
              {row.note}
            </p>
          ) : null}
        </CardBody>
      </Card>
    </li>
  )
}
