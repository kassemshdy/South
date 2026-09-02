import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, KeyRound, Phone } from 'lucide-react'
import { useState } from 'react'
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
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { otpSchema, phoneSchema } from '@/utils/validation'

type PhoneValues = z.infer<typeof phoneSchema>
type OtpValues = z.infer<typeof otpSchema>

export function LoginPage() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [phone, setPhone] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)

  useSeo({ title: 'تسجيل الدخول | دليل الجنوب', noIndex: true })

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/dashboard'
  if (isAuthenticated) return <Navigate to={redirectTo} replace />

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          {step === 'phone' ? (
            <PhoneStep
              onSent={(phoneNumber, debugCode) => {
                setPhone(phoneNumber)
                setDevCode(debugCode)
                setStep('code')
              }}
            />
          ) : (
            <CodeStep
              phone={phone}
              devCode={devCode}
              redirectTo={redirectTo}
              onBack={() => setStep('phone')}
            />
          )}
        </CardBody>
      </Card>
    </div>
  )
}

function PhoneStep({ onSent }: { onSent: (phone: string, debugCode: string | null) => void }) {
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<PhoneValues>({ resolver: zodResolver(phoneSchema) })

  const onSubmit = handleSubmit(async ({ phone_number }) => {
    setSubmitting(true)
    try {
      const response = await authApi.requestOtp(phone_number)
      toast.success('تم إرسال رمز التحقق', 'تحقق من رسائلك القصيرة.')
      onSent(phone_number, response.debug_code)
    } catch (error) {
      if (error instanceof ApiError) {
        setError('phone_number', { message: error.message })
      } else {
        toast.error('تعذر إرسال الرمز', 'يرجى المحاولة مجدداً.')
      }
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <>
      <div className="mb-6 text-center">
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-clay-600">
          <Phone className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="text-2xl">أدخل رقم هاتفك</h1>
        <p className="mt-2 text-ink-500">سنرسل لك رمز تحقق لمرة واحدة.</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label="رقم الهاتف" required error={errors.phone_number?.message} hint="مثال: 03123456 أو 71234567">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              {...register('phone_number')}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              dir="ltr"
              placeholder="03 123 456"
              className="ltr-nums text-center text-lg tracking-wide"
              invalid={Boolean(errors.phone_number)}
              autoFocus
            />
          )}
        </Field>

        <Button type="submit" size="lg" block loading={submitting}>
          إرسال رمز التحقق
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-500">
        بتسجيلك أنت توافق على نشر معلومات نشاطك بعد مراجعتها من فريق الإدارة.
      </p>
      <p className="mt-3 text-center text-sm">
        <Link to="/admin/login" className="text-clay-600 hover:underline">
          دخول المشرفين
        </Link>
      </p>
    </>
  )
}

function CodeStep({
  phone,
  devCode,
  redirectTo,
  onBack,
}: {
  phone: string
  devCode: string | null
  redirectTo: string
  onBack: () => void
}) {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<OtpValues>({
    resolver: zodResolver(otpSchema),
    defaultValues: { code: devCode ?? '' },
  })

  const onSubmit = handleSubmit(async ({ code }) => {
    setSubmitting(true)
    try {
      const token = await authApi.verifyOtp(phone, code)
      signIn(token)
      toast.success('مرحباً بك في دليل الجنوب')
      navigate(redirectTo, { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setError('code', { message: error.message })
      } else {
        toast.error('تعذر التحقق من الرمز')
      }
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <>
      <div className="mb-6 text-center">
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-clay-600">
          <KeyRound className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="text-2xl">أدخل رمز التحقق</h1>
        <p className="mt-2 text-ink-500">
          أرسلنا رمزاً إلى <span className="ltr-nums font-semibold text-ink-900">{phone}</span>
        </p>
      </div>

      {devCode ? (
        <p className="mb-5 rounded-xl border-2 border-dashed border-sand-300 bg-sand-50 p-3 text-center text-sm text-clay-700">
          وضع التطوير: الرمز هو <strong className="ltr-nums">{devCode}</strong>
        </p>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label="رمز التحقق" required error={errors.code?.message}>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              {...register('code')}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={8}
              dir="ltr"
              placeholder="123456"
              className="ltr-nums text-center text-2xl tracking-[0.4em]"
              invalid={Boolean(errors.code)}
              autoFocus
            />
          )}
        </Field>

        <Button type="submit" size="lg" block loading={submitting}>
          تأكيد وتسجيل الدخول
        </Button>

        <Button type="button" variant="ghost" block onClick={onBack}>
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
          تغيير رقم الهاتف
        </Button>
      </form>
    </>
  )
}
