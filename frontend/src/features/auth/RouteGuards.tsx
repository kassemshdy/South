import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { InlineSpinner } from '@/components/ui/States'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'

/**
 * Client-side guards are a navigation convenience only — the API enforces the
 * real authorization on every request.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()
  const t = useT()

  if (isLoading) return <InlineSpinner label={t('states.checkingSession')} />
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  // A password an administrator issued travelled through a WhatsApp message,
  // so the API refuses every owner route with 403 until it is replaced. The
  // redirect is the client half of that: without it the dashboard renders and
  // then fails one request at a time, with nothing saying why.
  if (user?.must_change_password) return <Navigate to="/change-password" replace />
  return <>{children}</>
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  const t = useT()

  if (isLoading) return <InlineSpinner label={t('states.checkingPermissions')} />
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" state={{ from: location.pathname }} replace />
  }
  if (!isAdmin) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}
