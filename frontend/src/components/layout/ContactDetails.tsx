import { Mail, MessageCircle, Phone } from 'lucide-react'

import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'
import { telHref, whatsappHref } from '@/utils/format'

/**
 * How to reach the team: phone, WhatsApp and email, each as a link, from the
 * site settings an administrator fills in. A detail that is not set is not
 * shown, and with none set this renders nothing.
 *
 * `large` is the contact page's card layout; the default is the footer's
 * compact list.
 */
export function ContactDetails({ large = false }: { large?: boolean }) {
  const t = useT()
  const { settings } = useSiteSettings()
  if (!settings) return null

  const rows: {
    key: string
    icon: typeof Phone
    labelKey: TranslationKey
    value: string
    href: string | null
  }[] = []
  if (settings.contact_phone) {
    rows.push({
      key: 'phone',
      icon: Phone,
      labelKey: 'contactChannel.PHONE',
      value: settings.contact_phone,
      href: telHref(settings.contact_phone),
    })
  }
  if (settings.contact_whatsapp) {
    rows.push({
      key: 'whatsapp',
      icon: MessageCircle,
      labelKey: 'platform.WHATSAPP',
      value: settings.contact_whatsapp,
      href: whatsappHref(settings.contact_whatsapp),
    })
  }
  if (settings.contact_email) {
    rows.push({
      key: 'email',
      icon: Mail,
      labelKey: 'contactChannel.EMAIL',
      value: settings.contact_email,
      href: `mailto:${settings.contact_email}`,
    })
  }
  if (rows.length === 0) return null

  return (
    <ul className={cn(large ? 'grid gap-4 sm:grid-cols-3' : 'space-y-3')}>
      {rows.map((row) => {
        const Icon = row.icon
        return (
          <li key={row.key}>
            <a
              href={row.href ?? undefined}
              target={row.key === 'whatsapp' ? '_blank' : undefined}
              rel={row.key === 'whatsapp' ? 'noopener noreferrer' : undefined}
              className={cn(
                'group flex items-center gap-3',
                large &&
                  'h-full rounded-2xl bg-white p-5 shadow-card ring-1 ring-ink-100 transition-colors hover:ring-brand-600',
              )}
            >
              <span
                className={cn(
                  'flex shrink-0 items-center justify-center rounded-full bg-sand-100 text-brand-700',
                  large ? 'h-12 w-12' : 'h-9 w-9',
                )}
              >
                <Icon className={large ? 'h-6 w-6' : 'h-4 w-4'} aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm text-ink-500">{t(row.labelKey)}</span>
                {/* Numbers and addresses read left to right in either language;
                    inline-block so the line still sits on the page's own side. */}
                <span className="block">
                  <span
                    dir="ltr"
                    className={cn(
                      'inline-block max-w-full truncate font-semibold text-ink-900 group-hover:text-brand-700',
                      large && 'text-lg',
                    )}
                  >
                    {row.value}
                  </span>
                </span>
              </span>
            </a>
          </li>
        )
      })}
    </ul>
  )
}
