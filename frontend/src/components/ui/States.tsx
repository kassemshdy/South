import { AlertTriangle, Inbox, SearchX, WifiOff } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-ink-100 bg-white/60 px-6 py-14 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-sand-100 text-brand-700">
        {icon ?? <Inbox className="h-7 w-7" aria-hidden="true" />}
      </div>
      <h3 className="text-lg font-bold text-ink-900">{title}</h3>
      {description ? <p className="mt-2 max-w-md text-ink-500">{description}</p> : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}

export function NoSearchResults({ onReset }: { onReset?: () => void }) {
  const t = useT()
  return (
    <EmptyState
      icon={<SearchX className="h-7 w-7" aria-hidden="true" />}
      title={t('states.noResultsTitle')}
      description={t('states.noResultsDescription')}
      action={
        onReset ? (
          <Button variant="outline" onClick={onReset}>
            {t('states.clearFilters')}
          </Button>
        ) : null
      }
    />
  )
}

/**
 * Error state that distinguishes a lost connection from a server failure —
 * the two need different actions from the user.
 */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useT()
  const isOffline = error instanceof ApiError && error.isNetworkError
  const message = error instanceof ApiError ? error.message : t('states.errorFallback')

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-2xl border-2 border-clay-200 bg-clay-50 px-6 py-12 text-center"
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-clay-100 text-clay-600">
        {isOffline ? (
          <WifiOff className="h-7 w-7" aria-hidden="true" />
        ) : (
          <AlertTriangle className="h-7 w-7" aria-hidden="true" />
        )}
      </div>
      <h3 className="text-lg font-bold text-clay-900">
        {isOffline ? t('states.offlineTitle') : t('states.errorTitle')}
      </h3>
      <p className="mt-2 max-w-md text-clay-700">{message}</p>
      {onRetry ? (
        <Button className="mt-6" variant="outline" onClick={onRetry}>
          {t('states.retry')}
        </Button>
      ) : null}
    </div>
  )
}

export function InlineSpinner({ label }: { label?: string }) {
  const t = useT()
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-ink-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-ink-100 border-t-brand-600" />
      <span>{label ?? t('states.loading')}</span>
    </div>
  )
}
