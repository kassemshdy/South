import { useMutation } from '@tanstack/react-query'
import { Eye } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n } from '@/i18n'
import { ApiError, viewAsStorage } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'

/**
 * Opens an owner's own session in this tab, at `to` (their dashboard by
 * default; a shop's Products page from the shop's admin and Shopify pages,
 * the owner's request of 5 Nov 2026).
 *
 * Shown to managers and reviewers, the roles that may look at an owner's
 * account. The API decides the rest: a manager's session saves changes, a
 * reviewer's is read-only, and neither reaches the owner's password or the
 * account's deletion.
 */
export function ViewAsButton({
  userId,
  to = '/dashboard',
  size = 'sm',
}: {
  userId: string
  to?: string
  size?: 'sm' | 'md'
}) {
  const { t } = useI18n()
  const toast = useToast()
  const allowed = useStaffCan('moderate')
  const open = useMutation({
    mutationFn: () => adminApi.viewAs(userId),
    onSuccess: (session) => {
      const started = viewAsStorage.start({
        token: session.access_token,
        userId: session.user_id,
        name: session.display_name,
        expiresAt: session.expires_at,
        canEdit: session.can_edit,
      })
      if (started) window.location.assign(to)
      else toast.error(t('viewAs.failed'))
    },
    onError: (error) =>
      toast.error(t('viewAs.failed'), error instanceof ApiError ? error.message : undefined),
  })
  if (!allowed) return null
  return (
    <Button variant="outline" size={size} loading={open.isPending} onClick={() => open.mutate()}>
      <Eye className="h-4 w-4" aria-hidden="true" />
      {t('viewAs.open')}
    </Button>
  )
}
