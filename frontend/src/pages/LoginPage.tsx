/**
 * Signing in as an owner.
 *
 * Two ways in, and they are not equals. The password is the one that works
 * today: it needs no SMS or WhatsApp gateway, and a gateway has not been
 * obtainable, so it is what an approved applicant is handed and therefore the
 * step shown first. The OTP path is kept behind a link rather than deleted —
 * the account is keyed by phone number either way, so a gateway arriving
 * later opens a second door onto the same account rather than a migration.
 *
 * Someone with no account at all is sent to apply, because that is now the
 * only route onto the site: there is no self-service sign-up, an
 * administrator audits every application, and the credentials come back over
 * WhatsApp.
 */

import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, KeyRound, Lock, Phone } from 'lucide-react'
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
import { serverFieldErrors } from '@/utils/serverFieldErrors'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { otpSchema, ownerLoginSchema, phoneSchema } from '@/utils/validation'

type PhoneValues = z.infer<ReturnType<typeof phoneSchema>>
type OtpValues = z.infer<ReturnType<typeof otpSchema>>

type Step = 'password' | 'phone' | 'code'

export function LoginPage() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  const t = useT()
  const [step, setStep] = useState<Step>('password')
  const [phone, setPhone] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)

  useSeo({ title: t('login.seoTitle'), noIndex: true })

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/dashboard'
  if (isAuthenticated) return <Navigate to={redirectTo} replace />

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          {step === 'password' ? (
            <PasswordStep redirectTo={redirectTo} onUseCode={() => setStep('phone')} />
          ) : step === 'phone' ? (
            <PhoneStep
              onSent={(phoneNumber, debugCode) => {
                setPhone(phoneNumber)
                setDevCode(debugCode)
                setStep('code')
              }}
              onUsePassword={() => setStep('password')}
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

type OwnerLoginValues = z.infer<ReturnType<typeof ownerLoginSchema>>

function PasswordStep({
  redirectTo,
  onUseCode,
}: {
  redirectTo: string
  onUseCode: () => void
}) {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const t = useT()
  const [submitting, setSubmitting] = useState(false)
  const schema = useMemo(() => ownerLoginSchema(t), [t])

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<OwnerLoginValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async ({ phone_number, password }) => {
    setSubmitting(true)
    try {
      const token = await authApi.login(phone_number, password)
      signIn(token)
      toast.success(t('login.welcome'))
      // A password an administrator issued opens exactly one screen. Sending
      // them anywhere else would land on a 403 they cannot act on.
      navigate(token.user.must_change_password ? '/change-password' : redirectTo, {
        replace: true,
      })
    } catch (error) {
      if (error instanceof ApiError) {
        // One message for a wrong password and for a number with no account,
        // because the API deliberately answers both the same way — showing it
        // on the password field would claim a distinction it did not make.
        setError('password', { message: error.message })
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
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
          <Lock className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="text-2xl">{t('login.passwordTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('login.passwordSubtitle')}</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label={t('login.phoneLabel')} required error={errors.phone_number?.message}>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              {...register('phone_number')}
              type="tel"
              inputMode="tel"
              autoComplete="username"
              dir="ltr"
              placeholder="03 123 456"
              className="ltr-nums"
              invalid={Boolean(errors.phone_number)}
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

      <p className="mt-4 text-center text-sm">
        <button type="button" onClick={onUseCode} className="text-brand-700 hover:underline">
          {t('login.useCodeInstead')}
        </button>
      </p>
      <p className="mt-3 text-center text-sm">
        <Link to="/admin/login" className="text-brand-700 hover:underline">
          {t('login.adminLink')}
        </Link>
      </p>
    </>
  )
}

function PhoneStep({
  onSent,
  onUsePassword,
}: {
  onSent: (phone: string, debugCode: string | null) => void
  onUsePassword: () => void
}) {
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
        // The field's own sentence when the API sent one, the envelope
        // otherwise — on a one-field form the envelope is the next best
        // thing, but "enter a valid Lebanese number" beats "check the
        // fields below" when it is on offer.
        const message = serverFieldErrors(error)['phone_number'] ?? error.message
        setError('phone_number', { message })
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
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
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
        <button type="button" onClick={onUsePassword} className="text-brand-700 hover:underline">
          {t('login.usePasswordInstead')}
        </button>
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
        setError('code', { message: serverFieldErrors(error)['code'] ?? error.message })
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
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
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
