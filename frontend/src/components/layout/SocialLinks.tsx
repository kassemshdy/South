import { Facebook, Instagram, Music2 } from 'lucide-react'

import { useT, type TranslationKey } from '@/i18n'

/**
 * The project's own social accounts.
 *
 * Each URL comes from a `VITE_`-prefixed variable set per service in Railway,
 * and **a link with no URL is not rendered** — the same discipline the Sentry
 * DSN and the analytics id follow. A "follow us" row pointing at a placeholder
 * is worse than no row: it spends the one click someone was willing to give.
 *
 * So this component renders nothing at all until at least one account exists,
 * which means it can ship before the accounts do.
 */

interface Account {
  key: string
  href: string | undefined
  icon: typeof Instagram
  labelKey: TranslationKey
}

export function SocialLinks() {
  const t = useT()

  const accounts: Account[] = [
    {
      key: 'instagram',
      href: import.meta.env.VITE_SOCIAL_INSTAGRAM as string | undefined,
      icon: Instagram,
      labelKey: 'platform.INSTAGRAM',
    },
    {
      key: 'facebook',
      href: import.meta.env.VITE_SOCIAL_FACEBOOK as string | undefined,
      icon: Facebook,
      labelKey: 'platform.FACEBOOK',
    },
    {
      key: 'tiktok',
      href: import.meta.env.VITE_SOCIAL_TIKTOK as string | undefined,
      // lucide has no TikTok glyph; Music2 is the closest honest stand-in.
      icon: Music2,
      labelKey: 'platform.TIKTOK',
    },
  ]

  const live = accounts.filter((account) => Boolean(account.href))
  if (live.length === 0) return null

  return (
    <div>
      <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">
        {t('footer.followUs')}
      </h2>
      <ul className="flex items-center gap-3">
        {live.map((account) => {
          const Icon = account.icon
          return (
            <li key={account.key}>
              <a
                href={account.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={t(account.labelKey)}
                className="flex h-11 w-11 items-center justify-center rounded-xl bg-sand-100 text-brand-700 transition-colors hover:bg-brand-700 hover:text-white"
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
              </a>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
