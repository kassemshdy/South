import { useQuery } from '@tanstack/react-query'

import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useI18n, type TranslationKey } from '@/i18n'
import { menuApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { MenuItemId } from '@/types/api'

/**
 * The site's public sections, in the order the directory's owner asked for.
 *
 * One list, read by the header row, the header's drawer and the footer. It is
 * written here rather than in each of them because three hand-written copies
 * of one list is exactly how this repository has drifted before — see the note
 * in `features/onboarding/destinations.ts`, which records the same lesson
 * after "I want to buy" led to two different pages depending on which copy a
 * visitor pressed.
 *
 * The business directory is not in it and is linked from nowhere: the CEO asked
 * for the site to speak only of "goods and products" and "services and skills",
 * so a shop is reached through its products. `/businesses` still answers, for
 * links already shared, but nothing on the site points to it.
 */
export interface SiteSection {
  id: MenuItemId
  href: string
  labelKey: TranslationKey
  /** Shown only once an administrator has entered a way to reach the team. */
  needsContact?: boolean
}

export const SITE_SECTIONS: SiteSection[] = [
  // Back at the CEO's request, first in the row: a way home that is a word,
  // for visitors who do not know the logo is one.
  { id: 'home', href: '/', labelKey: 'nav.home' },
  { id: 'products', href: '/products', labelKey: 'nav.products' },
  // Services and job applications: one directory until the owners split it.
  { id: 'services', href: '/services', labelKey: 'nav.services' },
  { id: 'jobs', href: '/jobs', labelKey: 'nav.jobs' },
  // Openings the platform posts by hand (29 Oct 2026).
  { id: 'vacancies', href: '/vacancies', labelKey: 'nav.vacancies' },
  // The blog before the news, in the CEO's order.
  { id: 'blog', href: '/blog', labelKey: 'nav.blog' },
  { id: 'news', href: '/news', labelKey: 'nav.news' },
  // The platform's own training (29 Oct 2026).
  { id: 'workshops', href: '/workshops', labelKey: 'nav.workshops' },
  { id: 'about', href: '/about', labelKey: 'nav.about' },
  // "Contact us" left the menu (the owners' ticket, 29 Oct 2026): its details
  // are at the foot of the About page and in the footer; /contact still answers.
]

/** A section as the menu shows it: in its saved place, under its name. */
export interface ShownSection extends SiteSection {
  label: string
}

/**
 * The sections to show right now; read this rather than the list itself.
 *
 * An administrator orders, hides and renames them at /admin/menu (the owners'
 * request, 29 Oct 2026). Until that answer arrives -- or if it never does --
 * the menu is the list above under its catalog names, so it never renders
 * empty and never waits on the network.
 */
export function useSiteSections(): ShownSection[] {
  const { hasContact } = useSiteSettings()
  const { t, locale } = useI18n()
  const menu = useQuery({ queryKey: queryKeys.siteMenu, queryFn: menuApi.get, staleTime: 5 * 60_000 })
  const byId = new Map(SITE_SECTIONS.map((section) => [section.id, section]))
  const saved = menu.data?.items ?? SITE_SECTIONS.map((section) => ({
    id: section.id,
    visible: true,
    label_ar: null,
    label_en: null,
  }))
  const shown: ShownSection[] = []
  for (const item of saved) {
    const section = byId.get(item.id)
    if (!section || !item.visible) continue
    if (section.needsContact && !hasContact) continue
    const custom = locale === 'en' ? item.label_en : item.label_ar
    shown.push({ ...section, label: custom || t(section.labelKey) })
  }
  return shown
}
