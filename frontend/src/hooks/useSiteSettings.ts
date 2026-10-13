import { useQuery } from '@tanstack/react-query'

import { siteSettingsApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { SiteSettings } from '@/types/api'

/**
 * The site's own contact details and social accounts, as an administrator set
 * them. One request, cached for the visit: the header and footer both read it
 * on every page.
 *
 * `hasContact` is whether there is any way to reach the team at all -- the
 * contact page, and every link to it, only exist when there is.
 */
export function useSiteSettings(): { settings: SiteSettings | undefined; hasContact: boolean } {
  const query = useQuery({
    queryKey: queryKeys.siteSettings,
    queryFn: siteSettingsApi.get,
    staleTime: 10 * 60_000,
  })
  const settings = query.data
  const hasContact = Boolean(
    settings &&
      (settings.contact_phone ||
        settings.contact_whatsapp ||
        settings.contact_email ||
        settings.social_facebook ||
        settings.social_instagram),
  )
  return { settings, hasContact }
}

const SUPPORT_NUMBER = import.meta.env.VITE_SUPPORT_WHATSAPP as string | undefined

/**
 * The team's WhatsApp number: the one an administrator set at
 * /admin/site-settings, else `VITE_SUPPORT_WHATSAPP`, else null. Callers pass
 * it through `whatsappHref`, which also returns null for a number with no
 * digits in it, and render nothing then.
 */
export function useSupportWhatsapp(): string | null {
  const { settings } = useSiteSettings()
  return settings?.contact_whatsapp || SUPPORT_NUMBER || null
}
