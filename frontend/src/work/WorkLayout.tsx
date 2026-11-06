import { LayoutDashboard, Shield, User } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'

import { ScrollToTop } from '@/components/layout/ScrollToTop'
import { LocaleToggle } from '@/components/layout/LocaleToggle'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { FeedbackWidget } from '@/features/feedback/FeedbackWidget'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'
import { mainSiteUrl } from '@/work/site'

/**
 * Work's own frame: a light bar with its name, the two directories and the
 * way in, and a short footer that leads back to Janoubona. Nothing of the
 * main site's header, menu or footer.
 */
export function WorkLayout() {
  const t = useT()
  const { isAuthenticated, isAdmin } = useAuth()
  const navClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition-colors',
      isActive ? 'bg-brand-50 text-brand-800' : 'text-ink-700 hover:bg-sand-100',
    )

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <ScrollToTop />
      <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/95 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between gap-3">
          <Link to="/" className="flex min-w-0 items-baseline gap-2">
            <span className="text-xl font-extrabold text-brand-800" dir="ltr">
              {t('work.brand')}
            </span>
            <span className="hidden truncate text-sm text-ink-500 sm:inline">{t('work.tagline')}</span>
          </Link>
          <nav className="flex items-center gap-1" aria-label={t('nav.mainAria')}>
            <NavLink to="/services" className={navClass}>
              {t('nav.services')}
            </NavLink>
            <NavLink to="/jobs" className={cn(navClass({ isActive: false }), 'max-sm:hidden')}>
              {t('nav.jobs')}
            </NavLink>
            {isAdmin ? (
              <Button asChild size="sm" className="ms-1 shrink-0 whitespace-nowrap">
                <a href={mainSiteUrl('/admin')}>
                  <Shield className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                  {t('nav.adminPanel')}
                </a>
              </Button>
            ) : isAuthenticated ? (
              <Button asChild size="sm" className="ms-1 shrink-0 whitespace-nowrap">
                <Link to="/dashboard">
                  <LayoutDashboard className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                  {t('nav.myBusinesses')}
                </Link>
              </Button>
            ) : (
              <Button asChild size="sm" className="ms-1 shrink-0 whitespace-nowrap">
                <Link to="/login">
                  <User className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                  {t('nav.login')}
                </Link>
              </Button>
            )}
          </nav>
        </div>
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-ink-100 bg-sand-50">
        <div className="container-page flex flex-wrap items-center justify-between gap-3 py-6 text-sm text-ink-500">
          <span>
            <span dir="ltr">{t('work.brand')}</span> · {t('work.tagline')}
          </span>
          <div className="flex items-center gap-3">
            <a href={mainSiteUrl('/')} className="font-semibold text-brand-800 hover:underline">
              {t('app.name')}
            </a>
            <LocaleToggle />
          </div>
        </div>
      </footer>
      {isAuthenticated ? <FeedbackWidget /> : null}
    </div>
  )
}
