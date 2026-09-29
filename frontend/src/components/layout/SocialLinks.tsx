import { Facebook, Instagram, Music2 } from 'lucide-react'

import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'

/**
 * The project's own social accounts, as icon links.
 *
 * Facebook and Instagram come from the site settings an administrator fills
 * in (`/admin/site-settings`), so changing one needs no deploy. The
 * `VITE_SOCIAL_*` build variables still work as a fallback, and TikTok only
 * exists as one. **A link with no URL is not rendered**, and with none at all
 * this renders nothing: a "follow us" row pointing at a placeholder spends
 * the one click someone was willing to give.
 */

interface Account {
  key: string
  href: string
  icon: typeof Instagram
  labelKey: TranslationKey
}

export function useSocialAccounts(): Account[] {
  const { settings } = useSiteSettings()
  const candidates: (Omit<Account, 'href'> & { href: string | null | undefined })[] = [
    {
      key: 'facebook',
      href:
        settings?.social_facebook ??
        (import.meta.env.VITE_SOCIAL_FACEBOOK as string | undefined),
      icon: Facebook,
      labelKey: 'platform.FACEBOOK',
    },
    {
      key: 'instagram',
      href:
        settings?.social_instagram ??
        (import.meta.env.VITE_SOCIAL_INSTAGRAM as string | undefined),
      icon: Instagram,
      labelKey: 'platform.INSTAGRAM',
    },
    {
      key: 'tiktok',
      href: import.meta.env.VITE_SOCIAL_TIKTOK as string | undefined,
      // lucide has no TikTok glyph; Music2 is the closest honest stand-in.
      icon: Music2,
      labelKey: 'platform.TIKTOK',
    },
  ]
  return candidates.filter((account): account is Account => Boolean(account.href))
}

/** The icons alone; `compact` is the header's smaller size. */
export function SocialIcons({ compact = false }: { compact?: boolean }) {
  const t = useT()
  const accounts = useSocialAccounts()
  if (accounts.length === 0) return null

  return (
    <ul className={cn('flex items-center', compact ? 'gap-1' : 'gap-3')}>
      {accounts.map((account) => {
        const Icon = account.icon
        return (
          <li key={account.key}>
            <a
              href={account.href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t(account.labelKey)}
              className={cn(
                'flex items-center justify-center transition-colors',
                compact
                  ? 'h-10 w-10 rounded-full text-ink-700 hover:bg-sand-100 hover:text-brand-700'
                  : 'h-11 w-11 rounded-xl bg-sand-100 text-brand-700 hover:bg-brand-700 hover:text-white',
              )}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
            </a>
          </li>
        )
      })}
    </ul>
  )
}
