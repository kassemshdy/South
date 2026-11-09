import { Navigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/features/auth/AuthContext'
import { PhoneSignupCard, safeNext, usePhoneSignupEnabled } from '@/features/auth/PhoneSignup'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/** Sign-up by SMS code; with it switched off, the application form. */
export function SignupPage() {
  const t = useT()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuth()
  const enabled = usePhoneSignupEnabled()
  useSeo({ title: t('phoneSignup.signupTitle'), noIndex: true })

  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  if (enabled === undefined) return null
  if (!enabled) return <Navigate to="/register/business" replace />
  return <PhoneSignupCard mode="signup" next={safeNext(searchParams.get('next'))} />
}
