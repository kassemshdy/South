import { Link } from 'react-router-dom'

import { ContactDetails } from '@/components/layout/ContactDetails'
import { useSiteSections } from '@/components/layout/navigation'
import { SocialIcons } from '@/components/layout/SocialLinks'
import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'

export function Footer() {
  const t = useT()
  const { isAuthenticated } = useAuth()
  const sections = useSiteSections()
  const { hasContact } = useSiteSettings()

  return (
    <footer className="mt-20 border-t border-ink-100 bg-white">
      <div className="container-page grid gap-8 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          {/* As large as the header's, which grew so the logo reads. */}
          <img
            src="/janoubna-logo.webp"
            alt={t('app.name')}
            width={450}
            height={191}
            className="h-16 w-auto"
          />
          <p className="mt-3 max-w-sm leading-relaxed text-ink-500">{t('footer.tagline')}</p>
        </div>

        {/* Every heading in the header, from the same list the header reads. */}
        <nav aria-label={t('footer.sectionsAria')}>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
            {t('footer.sections')}
          </h2>
          <ul className="space-y-2 text-ink-500">
            {sections.map((section) => (
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

          {/* How to reach the team, and its social accounts -- whatever an
              administrator has filled in, and nothing at all until then. */}
          {hasContact ? (
            <div id="contact">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
                <Link to="/contact" className="hover:text-brand-700">
                  {t('nav.contact')}
                </Link>
              </h2>
              <div className="space-y-4">
                <ContactDetails />
                <SocialIcons />
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="border-t border-ink-100 py-5 text-center text-sm text-ink-500">
        {t('footer.copyright', { year: new Date().getFullYear() })}
      </div>
    </footer>
  )
}
