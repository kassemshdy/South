import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogClose, DialogContent } from '@/components/ui/Dialog'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'

/**
 * An administrator's permanent delete, behind a confirmation.
 *
 * The owners asked for it (round 3) for sellers and products. It cannot be
 * undone -- the API removes the rows and every file they pointed at -- so the
 * confirmation says what goes with it, in the caller's own words.
 */
export function DeleteForeverButton({
  description,
  onDelete,
  onDeleted,
  size = 'lg',
}: {
  /** What is about to go, already translated. */
  description: string
  onDelete: () => Promise<unknown>
  onDeleted?: () => void
  size?: 'sm' | 'lg'
}) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)

  const remove = useMutation({
    mutationFn: onDelete,
    onSuccess: () => {
      setOpen(false)
      toast.success(t('admin.deleted'))
      void queryClient.invalidateQueries({ queryKey: ['admin'] })
      onDeleted?.()
    },
    onError: (error) =>
      toast.error(t('admin.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button size={size} variant="danger" onClick={() => setOpen(true)}>
        <Trash2 className={size === 'lg' ? 'h-5 w-5' : 'h-4 w-4'} aria-hidden="true" />
        {t('admin.deleteForever')}
      </Button>
      <DialogContent title={t('admin.deleteForeverTitle')} description={description}>
        <div className="flex gap-3">
          <Button block variant="danger" loading={remove.isPending} onClick={() => remove.mutate()}>
            {t('admin.deleteForever')}
          </Button>
          <DialogClose asChild>
            <Button variant="outline" block>
              {t('common.cancel')}
            </Button>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  )
}
