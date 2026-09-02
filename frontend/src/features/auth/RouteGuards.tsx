import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { InlineSpinner } from '@/components/ui/States'
import { useAuth } from '@/features/auth/AuthContext'

/**
 * Client-side guards are a navigation convenience only — the API enforces the
 * real authorization on every request.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <InlineSpinner label="جارٍ التحقق من الجلسة…" />
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <>{children}</>
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <InlineSpinner label="جارٍ التحقق من الصلاحيات…" />
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" state={{ from: location.pathname }} replace />
  }
  if (!isAdmin) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}
