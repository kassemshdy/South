import { Suspense, lazy } from 'react'
import { Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { InlineSpinner } from '@/components/ui/States'
import { RequireAdmin, RequireAuth } from '@/features/auth/RouteGuards'
import { AboutPage } from '@/pages/AboutPage'
import { ArticleDetailPage } from '@/pages/ArticleDetailPage'
import { BlogPage } from '@/pages/BlogPage'
import { BusinessProfilePage } from '@/pages/BusinessProfilePage'
import { DirectoryPage } from '@/pages/DirectoryPage'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { NewsPage } from '@/pages/NewsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProductProfilePage } from '@/pages/ProductProfilePage'
import { ProductsDirectoryPage } from '@/pages/ProductsDirectoryPage'
import { TalentDirectoryPage } from '@/pages/TalentDirectoryPage'
import { TalentProfilePage } from '@/pages/TalentProfilePage'

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
const AdminFeedbackPage = lazy(() =>
  import('@/pages/admin/AdminFeedbackPage').then((m) => ({ default: m.AdminFeedbackPage })),
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
const AdminTalentReviewPage = lazy(() =>
  import('@/pages/admin/AdminTalentReviewPage').then((m) => ({
    default: m.AdminTalentReviewPage,
  })),
)
const AdminTalentSkillsPage = lazy(() =>
  import('@/pages/admin/AdminTalentSkillsPage').then((m) => ({
    default: m.AdminTalentSkillsPage,
  })),
)
const AdminTalentsPage = lazy(() =>
  import('@/pages/admin/AdminTalentsPage').then((m) => ({ default: m.AdminTalentsPage })),
)
const AdminUserDetailPage = lazy(() =>
  import('@/pages/admin/AdminUserDetailPage').then((m) => ({ default: m.AdminUserDetailPage })),
)
const AdminUsersPage = lazy(() =>
  import('@/pages/admin/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })),
)
const AdminTestimonialsPage = lazy(() =>
  import('@/pages/admin/AdminTestimonialsPage').then((m) => ({
    default: m.AdminTestimonialsPage,
  })),
)
const AdminArticlesPage = lazy(() =>
  import('@/pages/admin/AdminArticlesPage').then((m) => ({ default: m.AdminArticlesPage })),
)
const AccountPage = lazy(() =>
  import('@/pages/dashboard/AccountPage').then((m) => ({ default: m.AccountPage })),
)
const BusinessWizardPage = lazy(() =>
  import('@/pages/dashboard/BusinessWizardPage').then((m) => ({ default: m.BusinessWizardPage })),
)
const CartPage = lazy(() =>
  import('@/pages/CartPage').then((m) => ({ default: m.CartPage })),
)
const FavouritesPage = lazy(() =>
  import('@/pages/FavouritesPage').then((m) => ({ default: m.FavouritesPage })),
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
// The two application forms reuse the dashboard's own form components, so
// they carry the same weight; a visitor who never applies should not download
// them. `ChangePasswordPage` rides along for the same reason.
const ChangePasswordPage = lazy(() =>
  import('@/pages/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })),
)
const RegisterBusinessPage = lazy(() =>
  import('@/pages/RegisterBusinessPage').then((m) => ({ default: m.RegisterBusinessPage })),
)
const RegisterTalentPage = lazy(() =>
  import('@/pages/RegisterTalentPage').then((m) => ({ default: m.RegisterTalentPage })),
)

const TalentDashboardPage = lazy(() =>
  import('@/pages/dashboard/TalentDashboardPage').then((m) => ({
    default: m.TalentDashboardPage,
  })),
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
          <Route path="products" element={<ProductsDirectoryPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="favourites" element={<FavouritesPage />} />
          <Route path="product/:slug" element={<ProductProfilePage />} />
          <Route path="talent" element={<TalentDirectoryPage />} />
          <Route path="talent/:slug" element={<TalentProfilePage />} />
          <Route path="news" element={<NewsPage />} />
          <Route path="blog" element={<BlogPage />} />
          <Route path="articles/:slug" element={<ArticleDetailPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="admin/login" element={<AdminLoginPage />} />
          {/* Applying needs no account — it is how you get one. */}
          <Route path="register/business" element={<RegisterBusinessPage />} />
          <Route path="register/talent" element={<RegisterTalentPage />} />
          {/* Outside RequireAuth on purpose: that guard sends an account with
              an issued password *here*, so guarding this with it would loop. */}
          <Route path="change-password" element={<ChangePasswordPage />} />

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
            path="dashboard/account"
            element={
              <RequireAuth>
                <AccountPage />
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
          <Route
            path="dashboard/talent"
            element={
              <RequireAuth>
                <TalentDashboardPage />
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
            <Route path="talent" element={<AdminTalentsPage />} />
            <Route path="talent/:id" element={<AdminTalentReviewPage />} />
            <Route path="categories" element={<AdminCategoriesPage />} />
            <Route path="talent-skills" element={<AdminTalentSkillsPage />} />
            <Route path="locations" element={<AdminLocationsPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="users/:id" element={<AdminUserDetailPage />} />
            <Route path="feedback" element={<AdminFeedbackPage />} />
            <Route path="testimonials" element={<AdminTestimonialsPage />} />
            <Route path="articles" element={<AdminArticlesPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
