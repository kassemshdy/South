import { zodResolver } from '@hookform/resolvers/zod'
import { Shield } from 'lucide-react'
import { useState } from 'react'
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
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { adminLoginSchema } from '@/utils/validation'

type AdminLoginValues = z.infer<typeof adminLoginSchema>

export function AdminLoginPage() {
  const { signIn, isAdmin } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)

  useSeo({ title: 'دخول المشرفين | دليل الجنوب', noIndex: true })

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<AdminLoginValues>({ resolver: zodResolver(adminLoginSchema) })

  if (isAdmin) return <Navigate to="/admin" replace />

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setSubmitting(true)
    try {
      const token = await authApi.adminLogin(email, password)
      signIn(token)
      navigate('/admin', { replace: true })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'تعذر تسجيل الدخول.'
      // Deliberately attached to the password field: the API does not reveal
      // whether the email exists, and neither should the UI.
      setError('password', { message })
      toast.error('فشل تسجيل الدخول', message)
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
            <h1 className="text-2xl">دخول المشرفين</h1>
            <p className="mt-2 text-ink-500">هذه الصفحة مخصصة لفريق إدارة الدليل.</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5" noValidate>
            <Field label="البريد الإلكتروني" required error={errors.email?.message}>
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

            <Field label="كلمة المرور" required error={errors.password?.message}>
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
              تسجيل الدخول
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
