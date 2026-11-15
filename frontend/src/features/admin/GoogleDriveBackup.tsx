import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n, useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDateTime } from '@/utils/format'

/**
 * The copy of every file -- photos, ID scans, database backups -- in a Google
 * Drive folder (the owners' decision, 13 Nov 2026). The manager connects it
 * here with their Google account; Google sends them back with
 * `?gdrive=connected` or `?gdrive=error`, which this card announces once.
 */
export function GoogleDriveBackup() {
  const t = useT()
  const { locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canManage = useStaffCan('manage')
  const [params, setParams] = useSearchParams()

  const status = useQuery({ queryKey: queryKeys.adminGdrive, queryFn: adminApi.gdriveStatus })

  useEffect(() => {
    const outcome = params.get('gdrive')
    if (!outcome) return
    if (outcome === 'connected') toast.success(t('gdrive.connectedNotice'))
    else toast.error(t('gdrive.failedNotice'))
    params.delete('gdrive')
    setParams(params, { replace: true })
  }, [params, setParams, toast, t])

  const onError = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const connect = useMutation({
    mutationFn: adminApi.gdriveConnect,
    // Off to Google's own sign-in; it comes back to this page.
    onSuccess: ({ url }) => window.location.assign(url),
    onError,
  })
  const disconnect = useMutation({
    mutationFn: adminApi.gdriveDisconnect,
    onSuccess: (next) => queryClient.setQueryData(queryKeys.adminGdrive, next),
    onError,
  })
  const run = useMutation({
    mutationFn: adminApi.gdriveRun,
    onSuccess: ({ message }) => toast.success(message),
    onError,
  })

  const data = status.data
  const last = data?.last_run

  return (
    <Card>
      <CardBody className="space-y-3">
        <h2 className="font-bold">{t('gdrive.title')}</h2>
        <p className="text-sm text-ink-500">{t('gdrive.body')}</p>

        {status.isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : status.isError ? (
          <ErrorState error={status.error} onRetry={() => void status.refetch()} />
        ) : data?.service_account ? (
          <p className="text-sm text-olive-700">{t('gdrive.serviceAccount')}</p>
        ) : !data?.available ? (
          <p className="text-sm text-clay-700">{t('gdrive.notConfigured')}</p>
        ) : data.connected ? (
          <div className="space-y-2 text-sm">
            <p className="font-semibold text-olive-700">
              {t('gdrive.connectedAs', { email: data.email ?? '' })}
            </p>
            {data.folder_url ? (
              <a
                href={data.folder_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-700 hover:underline"
              >
                {t('gdrive.openFolder')}
              </a>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-ink-500">{t('gdrive.notConnected')}</p>
        )}

        {last ? (
          <p className="text-xs text-ink-500 ltr-nums">
            {last.error
              ? t('gdrive.lastRunFailed', { date: formatDateTime(last.at, locale) })
              : t('gdrive.lastRun', {
                  date: formatDateTime(last.at, locale),
                  copied: last.copied ?? 0,
                  already: last.already ?? 0,
                  failed: last.failed ?? 0,
                })}
          </p>
        ) : null}

        {canManage && data && !data.service_account && data.available ? (
          <div className="flex flex-wrap gap-2">
            {data.connected ? (
              <>
                <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
                  {t('gdrive.runNow')}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => disconnect.mutate()}
                  disabled={disconnect.isPending}
                >
                  {t('gdrive.disconnect')}
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={() => connect.mutate()} disabled={connect.isPending}>
                {t('gdrive.connect')}
              </Button>
            )}
          </div>
        ) : null}
      </CardBody>
    </Card>
  )
}
