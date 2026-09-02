import { Suspense, lazy } from 'react'
import { Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { InlineSpinner } from '@/components/ui/States'
import { RequireAdmin, RequireAuth } from '@/features/auth/RouteGuards'
import { BusinessProfilePage } from '@/pages/BusinessProfilePage'
import { DirectoryPage } from '@/pages/DirectoryPage'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

/**
 * Public pages ship in the main bundle; the owner dashboard and admin area are
 * loaded on demand. Most visitors never sign in, and they should not pay to
 * download screens they will never open — this matters on mobile data.
 */
const AdminBusinessesPage = lazy(() =>
  import('@/pages/admin/AdminBusinessesPage').then((m) => ({ default: m.AdminBusinessesPage })),
)
const AdminCategoriesPage = lazy(() =>
  import('@/pages/admin/AdminCategoriesPage').then((m) => ({ default: m.AdminCategoriesPage })),
)
const AdminDashboardPage = lazy(() =>
  import('@/pages/admin/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage })),
)
const AdminLayout = lazy(() =>
  import('@/pages/admin/AdminLayout').then((m) => ({ default: m.AdminLayout })),
)
const AdminLocationsPage = lazy(() =>
  import('@/pages/admin/AdminLocationsPage').then((m) => ({ default: m.AdminLocationsPage })),
)
const AdminLoginPage = lazy(() =>
  import('@/pages/admin/AdminLoginPage').then((m) => ({ default: m.AdminLoginPage })),
)
const AdminReviewPage = lazy(() =>
  import('@/pages/admin/AdminReviewPage').then((m) => ({ default: m.AdminReviewPage })),
)
const AdminUsersPage = lazy(() =>
  import('@/pages/admin/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })),
)
const BusinessWizardPage = lazy(() =>
  import('@/pages/dashboard/BusinessWizardPage').then((m) => ({ default: m.BusinessWizardPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const EditBusinessPage = lazy(() =>
  import('@/pages/dashboard/EditBusinessPage').then((m) => ({ default: m.EditBusinessPage })),
)
const ItemsPage = lazy(() =>
  import('@/pages/dashboard/ItemsPage').then((m) => ({ default: m.ItemsPage })),
)

export function App() {
  return (
    <Suspense fallback={<InlineSpinner />}>
      <Routes>
        <Route element={<AppLayout />}>
          {/* Public — no account required */}
          <Route index element={<HomePage />} />
          <Route path="businesses" element={<DirectoryPage />} />
          <Route path="business/:slug" element={<BusinessProfilePage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="admin/login" element={<AdminLoginPage />} />

          {/* Business owner */}
          <Route
            path="dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="dashboard/businesses/new"
            element={
              <RequireAuth>
                <BusinessWizardPage />
              </RequireAuth>
            }
          />
          <Route
            path="dashboard/businesses/:id/edit"
            element={
              <RequireAuth>
                <EditBusinessPage />
              </RequireAuth>
            }
          />
          <Route
            path="dashboard/businesses/:id/items"
            element={
              <RequireAuth>
                <ItemsPage />
              </RequireAuth>
            }
          />

          {/* Administrator */}
          <Route
            path="admin"
            element={
              <RequireAdmin>
                <AdminLayout />
              </RequireAdmin>
            }
          >
            <Route index element={<AdminDashboardPage />} />
            <Route path="businesses" element={<AdminBusinessesPage />} />
            <Route path="businesses/:id" element={<AdminReviewPage />} />
            <Route path="categories" element={<AdminCategoriesPage />} />
            <Route path="locations" element={<AdminLocationsPage />} />
            <Route path="users" element={<AdminUsersPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
