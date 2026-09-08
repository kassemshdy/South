import { Link } from 'react-router-dom'
import { Store } from 'lucide-react'

import { SocialLinks } from '@/components/layout/SocialLinks'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'

export function Footer() {
  const t = useT()
  const { isAuthenticated } = useAuth()

  return (
    <footer className="mt-20 border-t border-ink-100 bg-white">
      <div className="container-page grid gap-8 py-12 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <div className="flex items-center gap-2.5 font-display text-lg font-bold">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white">
              <Store className="h-5 w-5" aria-hidden="true" />
            </span>
            {t('app.name')}
          </div>
          <p className="mt-3 max-w-sm leading-relaxed text-ink-500">{t('footer.tagline')}</p>
        </div>

        <nav aria-label={t('footer.quickLinksAria')}>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
            {t('footer.quickLinks')}
          </h2>
          <ul className="space-y-2 text-ink-500">
            <li>
              <Link to="/businesses" className="hover:text-clay-600">
                {t('nav.directory')}
              </Link>
            </li>
            <li>
              <Link to="/dashboard/businesses/new" className="hover:text-clay-600">
                {t('nav.addBusiness')}
              </Link>
            </li>
            <li>
              {isAuthenticated ? (
                <Link to="/dashboard" className="hover:text-clay-600">
                  {t('nav.myBusinesses')}
                </Link>
              ) : (
                <Link to="/login" className="hover:text-clay-600">
                  {t('nav.login')}
                </Link>
              )}
            </li>
          </ul>
        </nav>

        <div className="space-y-8">
          <div>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
              {t('footer.about')}
            </h2>
            <p className="leading-relaxed text-ink-500">{t('footer.aboutBody')}</p>
          </div>

          <SocialLinks />
        </div>
      </div>

      <div className="border-t border-ink-100 py-5 text-center text-sm text-ink-500">
        {t('footer.copyright', { year: new Date().getFullYear() })}
      </div>
    </footer>
  )
}
