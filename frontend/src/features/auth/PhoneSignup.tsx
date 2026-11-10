/**
 * The pieces of sign-up by SMS code that pages share: whether the site offers
 * it right now, the card that runs it, and the gate the application forms sit
 * behind while it is on.
 */

import { useQuery } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { PhoneCodeFlow } from '@/features/auth/PhoneCodeFlow'
import { useT } from '@/i18n'
import { phoneAuthApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/** True while an administrator has SMS sign-up on and the provider is set;
 * undefined until the answer arrives. */
export function usePhoneSignupEnabled(): boolean | undefined {
  const config = useQuery({
    queryKey: queryKeys.phoneAuthConfig,
    queryFn: phoneAuthApi.config,
    staleTime: 5 * 60_000,
  })
  if (config.isError) return false
  return config.data?.enabled
}

/** Only paths inside the dashboard: a ``next`` from the URL must not send a
 * freshly signed-in person to another site. */
export function safeNext(next: string | null, fallback = '/dashboard'): string {
  return next && next.startsWith('/dashboard') && !next.startsWith('//') ? next : fallback
}

export function PhoneSignupCard({
  mode,
  next,
  footer,
}: {
  mode: 'signup' | 'reset'
  next: string
  footer?: ReactNode
}) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const { signIn } = useAuth()

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
              <UserPlus className="h-6 w-6" aria-hidden="true" />
            </span>
            <h1 className="text-2xl">
              {mode === 'signup' ? t('phoneSignup.signupTitle') : t('phoneSignup.resetTitle')}
            </h1>
            <p className="mt-2 text-ink-500">
              {mode === 'signup' ? t('phoneSignup.signupBody') : t('phoneSignup.resetBody')}
            </p>
          </div>
          <PhoneCodeFlow
            mode={mode}
            onDone={(token) => {
              signIn(token)
              toast.success(
                mode === 'signup' ? t('phoneSignup.welcome') : t('phoneSignup.passwordSaved'),
              )
              navigate(next, { replace: true })
            }}
          />
          <div className="mt-6 space-y-2 text-center text-sm">
            {footer}
            <p>
              <Link to="/login" className="text-brand-700 hover:underline">
                {t('phoneSignup.haveAccount')}
              </Link>
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}

/**
 * While SMS sign-up is on, an application page opens on it, with the form one
 * tap away for whoever cannot receive the SMS. ``?form=1`` opens the form
 * directly, which is the link staff send to such a person.
 */
export function PhoneSignupGate({
  next,
  formRequested,
  children,
}: {
  next: string
  formRequested: boolean
  children: ReactNode
}) {
  const t = useT()
  const enabled = usePhoneSignupEnabled()
  const [useForm, setUseForm] = useState(formRequested)
  if (enabled === undefined && !formRequested) return null
  if (!enabled || useForm) return <>{children}</>
  return (
    <PhoneSignupCard
      mode="signup"
      next={next}
      footer={
        <p>
          <button
            type="button"
            className="text-brand-700 hover:underline"
            onClick={() => setUseForm(true)}
          >
            {t('phoneSignup.useForm')}
          </button>
        </p>
      }
    />
  )
}
