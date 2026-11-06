import { Suspense, lazy, useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { InlineSpinner } from '@/components/ui/States'
import { RequireAuth, RequireListingOwner } from '@/features/auth/RouteGuards'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { TalentDirectoryPage } from '@/pages/TalentDirectoryPage'
import { TalentProfilePage } from '@/pages/TalentProfilePage'
import { WorkHomePage } from '@/work/WorkHomePage'
import { WorkLayout } from '@/work/WorkLayout'
import { mainSiteUrl } from '@/work/site'

const ForgotPasswordPage = lazy(() =>
  import('@/pages/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage })),
)
const ChangePasswordPage = lazy(() =>
  import('@/pages/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })),
)
const RegisterTalentPage = lazy(() =>
  import('@/pages/RegisterTalentPage').then((m) => ({ default: m.RegisterTalentPage })),
)
const ServiceRequestPage = lazy(() =>
  import('@/pages/ServiceRequestPage').then((m) => ({ default: m.ServiceRequestPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const AccountPage = lazy(() =>
  import('@/pages/dashboard/AccountPage').then((m) => ({ default: m.AccountPage })),
)
const TalentDashboardPage = lazy(() =>
  import('@/pages/dashboard/TalentDashboardPage').then((m) => ({
    default: m.TalentDashboardPage,
  })),
)

/** Leaves Work for the same path on janoubona.net (the admin panel, a shop's tools). */
function ToMainSite() {
  useEffect(() => {
    window.location.replace(mainSiteUrl(window.location.pathname + window.location.search))
  }, [])
  return <InlineSpinner />
}

/**
 * Work.Janoubona's routes (phase 1: the shared talent directories and
 * profiles, and the account pages). Jobs and proposals, service packages,
 * messages and reviews arrive in the later phases.
 */
export function WorkApp() {
  return (
    <Suspense fallback={<InlineSpinner />}>
      <Routes>
        <Route element={<WorkLayout />}>
          <Route index element={<WorkHomePage />} />
          <Route path="services" element={<TalentDirectoryPage kind="SERVICE" />} />
          <Route path="services/request" element={<ServiceRequestPage />} />
          <Route path="jobs" element={<TalentDirectoryPage kind="JOB_SEEKER" />} />
          <Route path="talent" element={<Navigate to="/services" replace />} />
          <Route path="talent/:slug" element={<TalentProfilePage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
          <Route path="change-password" element={<ChangePasswordPage />} />
          <Route path="register/talent" element={<RegisterTalentPage />} />
          <Route
            path="dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="dashboard/account"
            element={
              <RequireAuth>
                <AccountPage />
              </RequireAuth>
            }
          />
          <Route
            path="dashboard/talent"
            element={
              <RequireAuth>
                <RequireListingOwner>
                  <TalentDashboardPage />
                </RequireListingOwner>
              </RequireAuth>
            }
          />
          {/* Staff work, shops and everything else belong to janoubona.net. */}
          <Route path="admin/*" element={<ToMainSite />} />
          <Route path="dashboard/businesses/*" element={<ToMainSite />} />
          <Route path="dashboard/orders/*" element={<ToMainSite />} />
          <Route path="business/*" element={<ToMainSite />} />
          <Route path="products/*" element={<ToMainSite />} />
          <Route path="product/*" element={<ToMainSite />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
