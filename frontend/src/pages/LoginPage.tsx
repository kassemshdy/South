/**
 * Signing in. One form, for everybody.
 *
 * One box for who you are and one for your password. An owner fills the first
 * with the phone number their account is keyed by, an administrator with their
 * email address, and the API tells them apart — so there is no "are you an
 * administrator?" question in front of a sign-in, which is a question nobody
 * should have to answer before they have proved anything.
 *
 * There used to be a second way in, a one-time code sent to the phone. It is
 * gone rather than hidden: no SMS or WhatsApp gateway was ever obtainable, so
 * the only provider that ever ran was the development one, which issues a
 * fixed code — on a deployment that is not a login, it is a way in for anyone
 * who knows a phone number.
 *
 * Someone with no account at all is sent to apply, because that is the only
 * route onto the site: there is no self-service sign-up, an administrator
 * audits every application, and the credentials come back over WhatsApp.
 */

import { zodResolver } from '@hookform/resolvers/zod'
import { Lock } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import type { z } from 'zod'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { signInSchema } from '@/utils/validation'

type SignInValues = z.infer<ReturnType<typeof signInSchema>>

export function LoginPage() {
  const { isAuthenticated, isAdmin, signIn } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const t = useT()
  const [submitting, setSubmitting] = useState(false)
  const schema = useMemo(() => signInSchema(t), [t])

  useSeo({ title: t('login.seoTitle'), noIndex: true })

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<SignInValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async ({ identifier, password }) => {
    setSubmitting(true)
    try {
      const token = await authApi.login(identifier, password)
      signIn(token)
      toast.success(t('login.welcome'))
      navigate(destinationFor(token, redirectTo), { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        // One message for a wrong password, an unknown number and an unknown
        // address, because the API deliberately answers all three the same
        // way — putting it on the identifier field would claim a distinction
        // it did not make.
        setError('password', { message: error.message })
      } else {
        toast.error(t('login.verifyFailed'))
      }
    } finally {
      setSubmitting(false)
    }
  })

  if (isAuthenticated) return <Navigate to={isAdmin ? '/admin' : redirectTo} replace />

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
              <Lock className="h-6 w-6" aria-hidden="true" />
            </span>
            <h1 className="text-2xl">{t('login.passwordTitle')}</h1>
            <p className="mt-2 text-ink-500">{t('login.passwordSubtitle')}</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5" noValidate>
            <Field
              label={t('login.identifierLabel')}
              required
              error={errors.identifier?.message}
              hint={t('login.identifierHint')}
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  {...register('identifier')}
                  type="text"
                  inputMode="tel"
                  autoComplete="username"
                  dir="ltr"
                  placeholder="03 123 456"
                  className="ltr-nums"
                  invalid={Boolean(errors.identifier)}
                  autoFocus
                />
              )}
            </Field>

            <Field
              label={t('login.passwordLabel')}
              required
              error={errors.password?.message}
              hint={t('login.passwordHint')}
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  {...register('password')}
                  type="password"
                  autoComplete="current-password"
                  dir="ltr"
                  invalid={Boolean(errors.password)}
                />
              )}
            </Field>

            <Button type="submit" size="lg" block loading={submitting}>
              {t('login.signIn')}
            </Button>
          </form>

          <p className="mt-6 rounded-xl bg-sand-100 p-3.5 text-center text-sm text-clay-800">
            {t('login.noAccount')}{' '}
            <Link to="/register/business" className="text-brand-700 hover:underline">
              {t('login.applyBusiness')}
            </Link>{' '}
            <span aria-hidden="true">·</span>{' '}
            <Link to="/register/talent" className="text-brand-700 hover:underline">
              {t('login.applyTalent')}
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  )
}

/**
 * Where a token lands.
 *
 * A password an administrator issued opens exactly one screen — sending
 * somebody anywhere else lands them on a 403 they cannot act on. Otherwise an
 * administrator goes to the panel, since `redirectTo` defaults to the owner
 * dashboard, which an administrator has no listings in.
 */
function destinationFor(
  token: { user: { must_change_password: boolean; role: string } },
  redirectTo: string,
): string {
  if (token.user.must_change_password) return '/change-password'
  if (token.user.role === 'ADMIN' && redirectTo === '/dashboard') return '/admin'
  return redirectTo
}
