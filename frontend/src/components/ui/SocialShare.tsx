import { Facebook, MessageCircle } from 'lucide-react'

import { useT } from '@/i18n'

/**
 * Share straight to WhatsApp or Facebook.
 *
 * `ShareButton` opens the phone's own share sheet, which already lists every
 * app, but on a computer it can only copy the link. These two are the
 * networks people here actually pass things around on, and both take a
 * plain link with no app key or account. Instagram has no share link for
 * the web, so it is not here.
 */
export function SocialShare({ text, url }: { text: string; url?: string | undefined }) {
  const t = useT()
  const target = url ?? window.location.href
  const links = [
    {
      key: 'whatsapp',
      href: `https://wa.me/?text=${encodeURIComponent(`${text}\n${target}`)}`,
      label: t('share.via', { platform: t('platform.WHATSAPP') }),
      icon: MessageCircle,
      tone: 'bg-[#25D366] text-white hover:bg-[#1ebe5a]',
    },
    {
      key: 'facebook',
      href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(target)}`,
      label: t('share.via', { platform: t('platform.FACEBOOK') }),
      icon: Facebook,
      tone: 'bg-[#1877F2] text-white hover:bg-[#0f66d8]',
    },
  ]

  return (
    <div className="flex gap-2">
      {links.map(({ key, href, label, icon: Icon, tone }) => (
        <a
          key={key}
          href={href}
          target="_blank"
          rel="noreferrer noopener"
          aria-label={label}
          title={label}
          className={`inline-flex h-11 w-11 items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${tone}`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </a>
      ))}
    </div>
  )
}
