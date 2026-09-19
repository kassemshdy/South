import type { TranslationKey } from '@/i18n'

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
 * The business directory is deliberately not in it. It is not one of the
 * headings, and the two surfaces reach it differently: the header as a search
 * icon, the footer as a named link.
 */
export interface SiteSection {
  href: string
  labelKey: TranslationKey
}

export const SITE_SECTIONS: SiteSection[] = [
  { href: '/products', labelKey: 'nav.products' },
  { href: '/talent', labelKey: 'nav.talent' },
  { href: '/news', labelKey: 'nav.news' },
  { href: '/blog', labelKey: 'nav.blog' },
  { href: '/about', labelKey: 'nav.about' },
]
