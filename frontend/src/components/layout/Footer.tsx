import { Link } from 'react-router-dom'

import { SITE_SECTIONS } from '@/components/layout/navigation'
import { SocialLinks } from '@/components/layout/SocialLinks'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'

export function Footer() {
  const t = useT()
  const { isAuthenticated } = useAuth()

  return (
    <footer className="mt-20 border-t border-ink-100 bg-white">
      <div className="container-page grid gap-8 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div className="flex flex-col items-start gap-1.5">
            <img
              src="/janoubna-logo.png"
              alt={t('app.name')}
              width={960}
              height={361}
              className="h-10 w-auto"
            />
            {/* Room for the full slogan here, where the header only has room
                for it from `sm` up. */}
            <span className="text-xs font-medium leading-tight text-ink-500">
              {t('app.slogan')}
            </span>
          </div>
          <p className="mt-3 max-w-sm leading-relaxed text-ink-500">{t('footer.tagline')}</p>
        </div>

        {/* Every heading in the header, from the same list the header reads,
            plus the directory — which the header carries as a search icon
            rather than a heading, and which somebody scanning a footer for
            the site's parts would expect to find named. */}
        <nav aria-label={t('footer.sectionsAria')}>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
            {t('footer.sections')}
          </h2>
          <ul className="space-y-2 text-ink-500">
            <li>
              <Link to="/businesses" className="hover:text-brand-700">
                {t('nav.directory')}
              </Link>
            </li>
            {SITE_SECTIONS.map((section) => (
              <li key={section.href}>
                <Link to={section.href} className="hover:text-brand-700">
                  {t(section.labelKey)}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <nav aria-label={t('footer.quickLinksAria')}>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
            {t('footer.quickLinks')}
          </h2>
          <ul className="space-y-2 text-ink-500">
            <li>
              <Link to="/dashboard/businesses/new" className="hover:text-brand-700">
                {t('nav.addBusiness')}
              </Link>
            </li>
            <li>
              {isAuthenticated ? (
                <Link to="/dashboard" className="hover:text-brand-700">
                  {t('nav.myBusinesses')}
                </Link>
              ) : (
                <Link to="/login" className="hover:text-brand-700">
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
