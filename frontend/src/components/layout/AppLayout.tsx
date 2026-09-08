import { Outlet } from 'react-router-dom'

import { Footer } from '@/components/layout/Footer'
import { Header } from '@/components/layout/Header'
import { ScrollToTop } from '@/components/layout/ScrollToTop'
import { useAuth } from '@/features/auth/AuthContext'
import { FeedbackWidget } from '@/features/feedback/FeedbackWidget'
import { useT } from '@/i18n'

export function AppLayout() {
  const t = useT()
  const { isAuthenticated } = useAuth()

  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      {/* Skip link: the first tab stop on every page. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-lg focus:bg-clay-500 focus:px-4 focus:py-2 focus:text-white"
      >
        {t('common.skipToContent')}
      </a>
      <Header />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      {/* Anyone signed in, not just admins. The whole reporting pipeline —
          screenshot, ticket, board — existed and was reachable only by the
          people who built it, so an owner whose upload failed had no way to
          say so. Anonymous reporting is a larger change (a nullable reporter
          and rate limiting) and is tracked separately. */}
      {isAuthenticated ? <FeedbackWidget /> : null}
    </div>
  )
}
