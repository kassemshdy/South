import { zodResolver } from '@hookform/resolvers/zod'
import { Shield } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
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
import { adminLoginSchema } from '@/utils/validation'

type AdminLoginValues = z.infer<ReturnType<typeof adminLoginSchema>>

export function AdminLoginPage() {
  const { signIn, isAdmin } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)
  const t = useT()
  const schema = useMemo(() => adminLoginSchema(t), [t])

  useSeo({ title: t('adminLogin.seoTitle'), noIndex: true })

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<AdminLoginValues>({ resolver: zodResolver(schema) })

  if (isAdmin) return <Navigate to="/admin" replace />

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setSubmitting(true)
    try {
      const token = await authApi.adminLogin(email, password)
      signIn(token)
      navigate('/admin', { replace: true })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t('adminLogin.fallbackError')
      // Deliberately attached to the password field: the API does not reveal
      // whether the email exists, and neither should the UI.
      setError('password', { message })
      toast.error(t('adminLogin.failed'), message)
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-olive-100 text-olive-700">
              <Shield className="h-6 w-6" aria-hidden="true" />
            </span>
            <h1 className="text-2xl">{t('adminLogin.title')}</h1>
            <p className="mt-2 text-ink-500">{t('adminLogin.subtitle')}</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5" noValidate>
            <Field label={t('adminLogin.email')} required error={errors.email?.message}>
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  {...register('email')}
                  type="email"
                  dir="ltr"
                  autoComplete="email"
                  className="ltr-nums"
                  invalid={Boolean(errors.email)}
                  autoFocus
                />
              )}
            </Field>

            <Field label={t('adminLogin.password')} required error={errors.password?.message}>
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  {...register('password')}
                  type="password"
                  dir="ltr"
                  autoComplete="current-password"
                  invalid={Boolean(errors.password)}
                />
              )}
            </Field>

            <Button type="submit" size="lg" block loading={submitting}>
              {t('adminLogin.submit')}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
