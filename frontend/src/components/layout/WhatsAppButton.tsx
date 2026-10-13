import { MessageCircle } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { useSupportWhatsapp } from '@/hooks/useSiteSettings'
import { useT } from '@/i18n'
import { whatsappHref } from '@/utils/format'

/**
 * A floating button that opens a WhatsApp chat with the team, on every page
 * a visitor or an owner might need help on.
 *
 * The number comes from `useSupportWhatsapp`; with none there is no button.
 *
 * Not on /admin: the people there are the ones it would reach. It sits on the
 * start side because the feedback button already holds the end corner.
 */
export function WhatsAppButton() {
  const t = useT()
  const { pathname } = useLocation()
  const href = whatsappHref(useSupportWhatsapp())
  if (!href || pathname.startsWith('/admin')) return null

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      aria-label={t('assisted.cta')}
      title={t('assisted.cta')}
      className="fixed bottom-5 start-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] text-white shadow-lift transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25D366] focus-visible:ring-offset-2"
    >
      <MessageCircle className="h-7 w-7" aria-hidden="true" />
    </a>
  )
}
