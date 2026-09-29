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
 * The business directory is not in it and is linked from nowhere: the CEO asked
 * for the site to speak only of "goods and products" and "services and skills",
 * so a shop is reached through its products. `/businesses` still answers, for
 * links already shared, but nothing on the site points to it.
 */
export interface SiteSection {
  href: string
  labelKey: TranslationKey
}

export const SITE_SECTIONS: SiteSection[] = [
  // Back at the CEO's request, first in the row: a way home that is a word,
  // for visitors who do not know the logo is one.
  { href: '/', labelKey: 'nav.home' },
  { href: '/products', labelKey: 'nav.products' },
  { href: '/talent', labelKey: 'nav.talent' },
  // The blog before the news, in the CEO's order.
  { href: '/blog', labelKey: 'nav.blog' },
  { href: '/news', labelKey: 'nav.news' },
  { href: '/about', labelKey: 'nav.about' },
]
