/**
 * Sign-up and password reset by SMS code, as three steps: the number (with
 * the captcha), the six-digit code, then the password. The same component
 * serves both, because the API does: the code proves the number, and the
 * password either opens the account or replaces a forgotten one.
 */

import { useMutation } from '@tanstack/react-query'
import { KeyRound, MessageSquareText, Smartphone } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Turnstile } from '@/components/ui/Turnstile'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { phoneAuthApi } from '@/services/api/endpoints'
import type { AuthToken } from '@/types/api'
import { isLebanesePhone, toAsciiDigits } from '@/utils/validation'

type Step = 'phone' | 'code' | 'password'

const RESEND_SECONDS = 60
const MIN_PASSWORD = 8

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export function PhoneCodeFlow({
  mode,
  onDone,
}: {
  mode: 'signup' | 'reset'
  onDone: (token: AuthToken) => void
}) {
  const t = useT()
  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [captcha, setCaptcha] = useState<string | null>(null)
  const [captchaKey, setCaptchaKey] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [wait, setWait] = useState(0)

  useEffect(() => {
    if (wait <= 0) return
    const timer = window.setTimeout(() => setWait((value) => value - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [wait])

  const send = useMutation({
    mutationFn: () => phoneAuthApi.sendCode(phone.trim(), captcha),
    onSuccess: () => {
      setStep('code')
      setCode('')
      setWait(RESEND_SECONDS)
      setError(null)
    },
    onError: (failure) => {
      setError(errorText(failure, t('states.errorFallback')))
      // A captcha token is good once; the next try needs a fresh one.
      setCaptcha(null)
      setCaptchaKey((value) => value + 1)
    },
  })

  const check = useMutation({
    mutationFn: () => phoneAuthApi.check(phone.trim(), code.trim()),
    onSuccess: () => {
      setStep('password')
      setError(null)
    },
    onError: (failure) => setError(errorText(failure, t('states.errorFallback'))),
  })

  const complete = useMutation({
    mutationFn: () => phoneAuthApi.complete(phone.trim(), code.trim(), password),
    onSuccess: onDone,
    onError: (failure) => {
      setError(errorText(failure, t('states.errorFallback')))
      if (failure instanceof ApiError && failure.status === 422) setStep('code')
    },
  })

  const submitPhone = () => {
    if (!phone.trim()) return setError(t('validation.phoneRequired'))
    if (!isLebanesePhone(phone)) return setError(t('validation.phoneInvalid'))
    send.mutate()
  }

  const submitCode = () => {
    if (!/^\d{6}$/.test(code.trim())) return setError(t('phoneSignup.codeInvalid'))
    check.mutate()
  }

  const submitPassword = () => {
    if (password.length < MIN_PASSWORD) return setError(t('phoneSignup.passwordTooShort'))
    if (password !== confirm) return setError(t('phoneSignup.passwordMismatch'))
    complete.mutate()
  }

  const onSubmit = { phone: submitPhone, code: submitCode, password: submitPassword }[step]

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      {step === 'phone' ? (
        <>
          <Field label={t('register.loginPhoneLabel')} required error={error ?? undefined}>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                dir="ltr"
                placeholder="71 123 456"
                className="ltr-nums"
                value={phone}
                onChange={(event) => {
                  setPhone(event.target.value)
                  if (error) setError(null)
                }}
                invalid={Boolean(error)}
                autoFocus
              />
            )}
          </Field>
          <Turnstile key={captchaKey} onToken={setCaptcha} />
          <Button type="submit" size="lg" block loading={send.isPending}>
            <Smartphone className="h-5 w-5" aria-hidden="true" />
            {t('phoneSignup.sendCode')}
          </Button>
        </>
      ) : null}

      {step === 'code' ? (
        <>
          <p className="text-sm text-ink-600">
            {t('phoneSignup.codeSentTo', { phone: `\u2066${phone.trim()}\u2069` })}
          </p>
          <Field label={t('phoneSignup.codeLabel')} required error={error ?? undefined}>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                inputMode="numeric"
                autoComplete="one-time-code"
                dir="ltr"
                maxLength={6}
                placeholder="000000"
                className="ltr-nums text-center text-2xl tracking-[0.5em]"
                value={code}
                onChange={(event) => {
                  setCode(toAsciiDigits(event.target.value).replace(/\D/g, '').slice(0, 6))
                  if (error) setError(null)
                }}
                invalid={Boolean(error)}
                autoFocus
              />
            )}
          </Field>
          <Button type="submit" size="lg" block loading={check.isPending}>
            <MessageSquareText className="h-5 w-5" aria-hidden="true" />
            {t('phoneSignup.verify')}
          </Button>
          <div className="flex items-center justify-between text-sm">
            <button
              type="button"
              className="text-brand-700 hover:underline"
              onClick={() => {
                setStep('phone')
                setError(null)
              }}
            >
              {t('phoneSignup.changeNumber')}
            </button>
            {wait > 0 ? (
              <span className="text-ink-400">{t('phoneSignup.resendIn', { seconds: wait })}</span>
            ) : (
              <button
                type="button"
                className="text-brand-700 hover:underline"
                onClick={() => {
                  setStep('phone')
                  setError(null)
                }}
              >
                {t('phoneSignup.resend')}
              </button>
            )}
          </div>
        </>
      ) : null}

      {step === 'password' ? (
        <>
          <Field
            label={t('phoneSignup.passwordLabel')}
            hint={t('phoneSignup.passwordHint')}
            required
          >
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="password"
                autoComplete="new-password"
                dir="ltr"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  if (error) setError(null)
                }}
                autoFocus
              />
            )}
          </Field>
          <Field label={t('phoneSignup.passwordConfirm')} required error={error ?? undefined}>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="password"
                autoComplete="new-password"
                dir="ltr"
                value={confirm}
                onChange={(event) => {
                  setConfirm(event.target.value)
                  if (error) setError(null)
                }}
                invalid={Boolean(error)}
              />
            )}
          </Field>
          <Button type="submit" size="lg" block loading={complete.isPending}>
            <KeyRound className="h-5 w-5" aria-hidden="true" />
            {mode === 'signup' ? t('phoneSignup.createAccount') : t('phoneSignup.savePassword')}
          </Button>
        </>
      ) : null}
    </form>
  )
}
