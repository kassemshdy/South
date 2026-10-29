import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, RotateCcw } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { DeleteForeverButton } from '@/features/admin/DeleteForeverButton'
import { TOPIC_KEYS } from '@/features/contact/topics'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/format'

/**
 * What the floating "ask us" button brought in, newest first. Administrators
 * only: each one is a stranger's name and a way to reach them. Handled like
 * the partner requests -- marked solved and kept in the archive, with
 * deleting left to the archive, for junk.
 */
export function AdminContactMessagesPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [archive, setArchive] = useState(false)
  const messages = useQuery({
    queryKey: queryKeys.adminContactMessages(archive),
    queryFn: () => adminApi.contactMessages(archive),
  })
  const moved = {
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin', 'contact-messages'] }),
    onError: () => toast.error(t('states.errorFallback')),
  }
  const solve = useMutation({ mutationFn: adminApi.solveContactMessage, ...moved })
  const reopen = useMutation({ mutationFn: adminApi.reopenContactMessage, ...moved })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.contactHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.contactSubtitle')}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {([false, true] as const).map((value) => (
          <button
            key={String(value)}
            type="button"
            aria-pressed={archive === value}
            onClick={() => setArchive(value)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
              archive === value
                ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
            )}
          >
            {t(value ? 'admin.partnersTabArchive' : 'admin.contactTabOpen')}
          </button>
        ))}
      </div>

      {messages.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : messages.isError ? (
        <ErrorState error={messages.error} onRetry={() => void messages.refetch()} />
      ) : messages.data && messages.data.length > 0 ? (
        <ul className="space-y-3">
          {messages.data.map((entry) => (
            <li key={entry.id}>
              <Card>
                <CardBody className="space-y-2">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink-900">{entry.name}</p>
                      {entry.phone ? (
                        <p className="ltr-nums text-sm text-ink-500" dir="ltr">
                          {entry.phone}
                        </p>
                      ) : null}
                      {entry.email ? (
                        <p className="text-sm text-ink-500" dir="ltr">
                          {entry.email}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge>{t(TOPIC_KEYS[entry.topic])}</Badge>
                      <span className="text-xs text-ink-300">
                        {formatDate(entry.created_at, locale)}
                      </span>
                    </div>
                  </div>
                  <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                    {entry.message}
                  </p>
                  {entry.page_path ? (
                    <p className="text-xs text-ink-500">
                      {t('admin.contactFromPage', { path: entry.page_path })}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    {entry.solved_at ? (
                      <>
                        <span className="me-auto text-xs text-ink-500">
                          {t('admin.partnerSolvedOn', { date: formatDate(entry.solved_at, locale) })}
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={reopen.isPending && reopen.variables === entry.id}
                          onClick={() => reopen.mutate(entry.id)}
                        >
                          <RotateCcw className="h-4 w-4" aria-hidden="true" />
                          {t('admin.partnerReopen')}
                        </Button>
                        <DeleteForeverButton
                          size="sm"
                          description={t('admin.contactDeleteBody')}
                          onDelete={() => adminApi.deleteContactMessage(entry.id)}
                        />
                      </>
                    ) : (
                      <Button
                        size="sm"
                        loading={solve.isPending && solve.variables === entry.id}
                        onClick={() => solve.mutate(entry.id)}
                      >
                        <Archive className="h-4 w-4" aria-hidden="true" />
                        {t('admin.partnerSolve')}
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t(archive ? 'admin.contactArchiveEmpty' : 'admin.contactEmpty')} />
      )}
    </div>
  )
}
