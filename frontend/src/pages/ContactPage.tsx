import { ContactDetails } from '@/components/layout/ContactDetails'
import { PageBanner } from '@/components/layout/PageBanner'
import { SocialIcons } from '@/components/layout/SocialLinks'
import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { NotFoundPage } from '@/pages/NotFoundPage'

/**
 * How to reach the team: whatever phone, WhatsApp, email and social accounts
 * an administrator has entered in the admin panel. Nothing links here until
 * at least one is set, and the page itself answers "not found" until then.
 */
export function ContactPage() {
  const t = useT()
  const { settings, hasContact } = useSiteSettings()
  useSeo({ title: t('nav.contact'), canonicalPath: '/contact' })

  if (settings && !hasContact) return <NotFoundPage />

  return (
    <>
      <PageBanner page="contact" title={t('nav.contact')} />
      <div className="container-page space-y-8 py-10 sm:py-14">
        <ContactDetails large />
        <SocialIcons />
      </div>
    </>
  )
}
