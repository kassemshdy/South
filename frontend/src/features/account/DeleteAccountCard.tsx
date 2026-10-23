import { useMutation } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'

/**
 * Deleting one's own account, which the owners asked sellers to be able to
 * do. Behind a dialog and the password, because it cannot be undone: every
 * listing, product and document goes with it.
 */
export function DeleteAccountCard() {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const { signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')

  const remove = useMutation({
    mutationFn: () => authApi.deleteAccount(password),
    onSuccess: (result) => {
      signOut()
      toast.success(result.message)
      navigate('/', { replace: true })
    },
    onError: (error) =>
      toast.error(
        t('account.deleteFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  return (
    <Card className="border-clay-300">
      <CardHeader>
        <h2 className="flex items-center gap-2 font-bold text-clay-800">
          <Trash2 className="h-5 w-5" aria-hidden="true" />
          {t('account.deleteHeading')}
        </h2>
      </CardHeader>
      <CardBody className="space-y-3">
        <p className="text-sm leading-relaxed text-ink-700">{t('account.deleteBody')}</p>
        <Button variant="danger" onClick={() => setOpen(true)}>
          {t('account.deleteHeading')}
        </Button>
      </CardBody>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setPassword('')
        }}
      >
        <DialogContent title={t('account.deleteHeading')} description={t('account.deleteBody')}>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              remove.mutate()
            }}
          >
            <Field label={t('account.deletePasswordLabel')} required>
              {(props) => (
                <Input
                  {...props}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              )}
            </Field>
            <Button type="submit" variant="danger" block loading={remove.isPending} disabled={!password}>
              {t('account.deleteConfirm')}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
