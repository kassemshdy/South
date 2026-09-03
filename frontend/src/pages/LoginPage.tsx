import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, KeyRound, Phone } from 'lucide-react'
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
import { otpSchema, phoneSchema } from '@/utils/validation'

type PhoneValues = z.infer<ReturnType<typeof phoneSchema>>
type OtpValues = z.infer<ReturnType<typeof otpSchema>>

export function LoginPage() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  const t = useT()
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [phone, setPhone] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)

  useSeo({ title: t('login.seoTitle'), noIndex: true })

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
  const t = useT()
  const [submitting, setSubmitting] = useState(false)
  const schema = useMemo(() => phoneSchema(t), [t])

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<PhoneValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async ({ phone_number }) => {
    setSubmitting(true)
    try {
      const response = await authApi.requestOtp(phone_number)
      toast.success(t('login.codeSent'), t('login.codeSentDescription'))
      onSent(phone_number, response.debug_code)
    } catch (error) {
      if (error instanceof ApiError) {
        setError('phone_number', { message: error.message })
      } else {
        toast.error(t('login.sendFailed'), t('login.sendFailedDescription'))
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
        <h1 className="text-2xl">{t('login.phoneTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('login.phoneSubtitle')}</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field
          label={t('login.phoneLabel')}
          required
          error={errors.phone_number?.message}
          hint={t('login.phoneHint')}
        >
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
          {t('login.sendCode')}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-500">{t('login.terms')}</p>
      <p className="mt-3 text-center text-sm">
        <Link to="/admin/login" className="text-clay-600 hover:underline">
          {t('login.adminLink')}
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
  const t = useT()
  const [submitting, setSubmitting] = useState(false)
  const schema = useMemo(() => otpSchema(t), [t])

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<OtpValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: devCode ?? '' },
  })

  const onSubmit = handleSubmit(async ({ code }) => {
    setSubmitting(true)
    try {
      const token = await authApi.verifyOtp(phone, code)
      signIn(token)
      toast.success(t('login.welcome'))
      navigate(redirectTo, { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setError('code', { message: error.message })
      } else {
        toast.error(t('login.verifyFailed'))
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
        <h1 className="text-2xl">{t('login.codeTitle')}</h1>
        <p className="mt-2 text-ink-500">
          {t('login.codeSubtitle')}{' '}
          <span className="ltr-nums font-semibold text-ink-900">{phone}</span>
        </p>
      </div>

      {devCode ? (
        <p className="mb-5 rounded-xl border-2 border-dashed border-sand-300 bg-sand-50 p-3 text-center text-sm text-clay-700">
          {t('login.devCodeNotice')} <strong className="ltr-nums">{devCode}</strong>
        </p>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label={t('login.codeLabel')} required error={errors.code?.message}>
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
          {t('login.confirm')}
        </Button>

        <Button type="button" variant="ghost" block onClick={onBack}>
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
          {t('login.changePhone')}
        </Button>
      </form>
    </>
  )
}
