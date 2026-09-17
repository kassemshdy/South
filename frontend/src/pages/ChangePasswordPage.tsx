/**
 * Replacing the password an administrator issued.
 *
 * The only screen an account in that state can reach, because the API refuses
 * every other owner route with 403 `password_change_required` until it is
 * done. That is not friction for its own sake: the password arrived in a
 * WhatsApp message, so anyone who has seen that chat could sign in with it.
 * Choosing a new one here ends every session opened with the old one —
 * including, deliberately, this one, which is why it finishes by signing in
 * again rather than carrying on.
 *
 * Also reachable voluntarily from the account screen by someone who simply
 * wants to change their password, which is the same operation.
 */

import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import type { z } from 'zod'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { serverFieldErrors } from '@/utils/serverFieldErrors'
import { changePasswordSchema } from '@/utils/validation'

type Values = z.infer<ReturnType<typeof changePasswordSchema>>

export function ChangePasswordPage() {
  const { user, isAuthenticated, isLoading, signIn, signOut } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const t = useT()
  const [submitting, setSubmitting] = useState(false)
  const schema = useMemo(() => changePasswordSchema(t), [t])

  useSeo({ title: t('password.seoTitle'), noIndex: true })

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    const phone = user?.phone_number ?? null
    setSubmitting(true)
    try {
      await authApi.changePassword(current_password, new_password)
      // The change invalidated the token this request was made with, so the
      // session has to be re-established rather than refreshed. An account
      // with no phone number cannot sign in on this route at all; it is sent
      // back to the login page instead of left holding a dead token.
      if (phone) {
        signIn(await authApi.login(phone, new_password))
        toast.success(t('password.changed'), t('password.changedDescription'))
        navigate('/dashboard', { replace: true })
      } else {
        signOut()
        toast.success(t('password.changed'), t('password.changedSignInAgain'))
        navigate('/login', { replace: true })
      }
    } catch (error) {
      if (error instanceof ApiError) {
        const fields = serverFieldErrors(error)
        setError('current_password', {
          message: fields['current_password'] ?? error.message,
        })
      } else {
        toast.error(t('password.failed'))
      }
    } finally {
      setSubmitting(false)
    }
  })

  // `isAuthenticated` is false while /api/me is still in flight, so checking it
  // alone would bounce a signed-in person to the login page on every reload of
  // this URL — and this is the one URL such an account is sent to.
  if (isLoading) return <InlineSpinner label={t('states.checkingSession')} />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
              <KeyRound className="h-6 w-6" aria-hidden="true" />
            </span>
            <h1 className="text-2xl">{t('password.title')}</h1>
            <p className="mt-2 text-ink-500">
              {user?.must_change_password ? t('password.forcedSubtitle') : t('password.subtitle')}
            </p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5" noValidate>
            <Field
              label={t('password.currentLabel')}
              required
              error={errors.current_password?.message}
              hint={user?.must_change_password ? t('password.currentHint') : undefined}
            >
              {(props) => (
                <Input
                  {...props}
                  {...register('current_password')}
                  type="password"
                  autoComplete="current-password"
                  dir="ltr"
                  invalid={Boolean(errors.current_password)}
                  autoFocus
                />
              )}
            </Field>

            <Field
              label={t('password.newLabel')}
              required
              error={errors.new_password?.message}
              hint={t('password.newHint')}
            >
              {(props) => (
                <Input
                  {...props}
                  {...register('new_password')}
                  type="password"
                  autoComplete="new-password"
                  dir="ltr"
                  invalid={Boolean(errors.new_password)}
                />
              )}
            </Field>

            <Field
              label={t('password.confirmLabel')}
              required
              error={errors.confirm_password?.message}
            >
              {(props) => (
                <Input
                  {...props}
                  {...register('confirm_password')}
                  type="password"
                  autoComplete="new-password"
                  dir="ltr"
                  invalid={Boolean(errors.confirm_password)}
                />
              )}
            </Field>

            <Button type="submit" size="lg" block loading={submitting}>
              {t('password.submit')}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
