import { ShieldAlert } from 'lucide-react'
import { Link, Navigate, useLocation } from 'react-router-dom'
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

/**
 * The two create forms, shut to an administrator.
 *
 * An administrator decides whether a listing may be published; owning one
 * puts them on both sides of that decision. The API refuses it outright —
 * `get_listing_owner` in `app/core/dependencies.py` — and this is the half
 * that says so on screen, because a form that submits and then fails is a
 * worse answer than a form that explains itself.
 *
 * A notice rather than a redirect: an administrator who followed a link here
 * should be told why it is closed, not silently moved somewhere else and left
 * wondering whether they mis-clicked.
 */
export function RequireListingOwner({ children }: { children: ReactNode }) {
  const { isAdmin, isLoading } = useAuth()
  const t = useT()

  if (isLoading) return <InlineSpinner label={t('states.checkingPermissions')} />
  if (!isAdmin) return <>{children}</>

  return (
    <div className="container-page max-w-xl py-16">
      <div className="rounded-2xl border-2 border-ink-100 bg-white p-8 text-center shadow-card">
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-olive-100 text-olive-700">
          <ShieldAlert className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="text-xl font-bold text-ink-900">{t('admin.cannotOwnTitle')}</h1>
        <p className="mt-3 leading-relaxed text-ink-500">{t('admin.cannotOwnBody')}</p>
        <Link
          to="/admin"
          className="mt-6 inline-block rounded-xl bg-brand-700 px-5 py-2.5 font-semibold text-white hover:bg-brand-800"
        >
          {t('nav.adminPanel')}
        </Link>
      </div>
    </div>
  )
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
