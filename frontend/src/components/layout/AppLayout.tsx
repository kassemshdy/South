import { Outlet } from 'react-router-dom'

import { Footer } from '@/components/layout/Footer'
import { Header } from '@/components/layout/Header'
import { RouteAnalytics } from '@/components/layout/RouteAnalytics'
import { ScrollToTop } from '@/components/layout/ScrollToTop'
import { WhatsAppButton } from '@/components/layout/WhatsAppButton'
import { useAuth } from '@/features/auth/AuthContext'
import { FeedbackWidget } from '@/features/feedback/FeedbackWidget'
import { OfferPopup } from '@/features/growth/OfferPopup'
import { useT } from '@/i18n'

export function AppLayout() {
  const t = useT()
  const { isAuthenticated } = useAuth()

  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      <RouteAnalytics />
      {/* Skip link: the first tab stop on every page. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-lg focus:bg-brand-800 focus:px-4 focus:py-2 focus:text-white"
      >
        {t('common.skipToContent')}
      </a>
      {/* `contents` keeps the header sticky; the wrappers exist only so a
          printed page (the admin growth report's PDF) is the content alone. */}
      <div className="contents print:hidden">
        <Header />
      </div>
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <div className="contents print:hidden">
        <Footer />
      </div>
      {/* Anyone signed in, not just admins. The whole reporting pipeline —
          screenshot, ticket, board — existed and was reachable only by the
          people who built it, so an owner whose upload failed had no way to
          say so. Anonymous reporting is a larger change (a nullable reporter
          and rate limiting) and is tracked separately. */}
      <div className="contents print:hidden">
        {isAuthenticated ? <FeedbackWidget /> : null}
        <WhatsAppButton />
        <OfferPopup />
      </div>
    </div>
  )
}
