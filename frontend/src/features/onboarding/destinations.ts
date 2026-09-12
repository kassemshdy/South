import { Package, Store, UserRound, Users } from 'lucide-react'

import type { TranslationKey } from '@/i18n'

/**
 * The doors into this site, written down once.
 *
 * This exists because the alternative was tried and failed. The homepage used
 * to ask "what do you want to do" in three separate widgets, each with its own
 * hand-written list of destinations, and the three drifted apart: "I want to
 * buy" led to `/products` in one and `/businesses` in another, and the hero's
 * offer card sent a carpenter to the *business* wizard because its copy said
 * "a good or a service" while its `href` said shop. Nobody decided any of
 * that; three copies of the same list simply stopped agreeing.
 *
 * So the destinations live here, and every surface that offers them —— the
 * popup on the homepage and the switcher above each directory —— renders this
 * same array. A door can be moved, renamed or removed in one place, and no
 * surface can quietly disagree with another.
 */
export interface Door {
  key: string
  icon: typeof Store
  /** The full sentence, for a card the visitor is choosing between. */
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  /** One or two words, for the switcher strip where space is a row. */
  shortKey: TranslationKey
  href: string
}

/**
 * Where someone looking for something can go. Three, because the directory
 * has three kinds of thing in it and a visitor who wants a carpenter, a jar
 * of honey and the shop on the corner is looking for three different shapes
 * of answer.
 */
export const BROWSE_DOORS: Door[] = [
  {
    key: 'businesses',
    icon: Store,
    titleKey: 'browse.businessesTitle',
    descriptionKey: 'browse.businessesDescription',
    shortKey: 'browse.businessesShort',
    href: '/businesses',
  },
  {
    key: 'products',
    icon: Package,
    // `/products`, not `/businesses`: someone who says they want to buy means
    // a thing with a price and an "add to order" button, not a list of shops
    // to work through.
    titleKey: 'onboarding.seekGoodsTitle',
    descriptionKey: 'onboarding.seekGoodsDescription',
    shortKey: 'browse.productsShort',
    href: '/products',
  },
  {
    key: 'talent',
    icon: Users,
    titleKey: 'onboarding.seekServiceTitle',
    descriptionKey: 'onboarding.seekServiceDescription',
    shortKey: 'browse.talentShort',
    href: '/talent',
  },
]

/**
 * Where someone with something to offer can go.
 *
 * Two, and the split is the whole point: a business is a place or a product,
 * a talent profile is the person themselves. Collapsing them into one card is
 * exactly the bug that sent a craftsperson into the shop wizard.
 *
 * **Both of these need an account**, which is a property of the set rather
 * than of either door —— you cannot list anything anonymously —— so it is
 * stated here once instead of as a flag repeated on each entry.
 */
export const OFFER_DOORS: Door[] = [
  {
    key: 'business',
    icon: Store,
    titleKey: 'onboarding.ownerTitle',
    descriptionKey: 'onboarding.ownerDescription',
    shortKey: 'onboarding.ownerShort',
    href: '/dashboard/businesses/new',
  },
  {
    key: 'talent',
    icon: UserRound,
    titleKey: 'onboarding.talentTitle',
    descriptionKey: 'onboarding.talentDescription',
    shortKey: 'onboarding.talentShort',
    href: '/dashboard/talent',
  },
]

/**
 * Which of the three directories a page is, so the switcher can mark it.
 * Typed off the doors themselves rather than restated, so a renamed door is a
 * compile error at every call site instead of a strip with nothing marked.
 */
export type BrowseKey = (typeof BROWSE_DOORS)[number]['key']

/**
 * The query parameters that survive a hop between directories.
 *
 * `q` and `location` mean the same thing in all three. `category` (businesses
 * and products) and `skill` (talent) do not map onto one another, and the
 * price bounds are products-only —— carrying those across would silently
 * apply a filter the destination cannot show or clear.
 */
export const SHARED_FILTERS = ['q', 'location'] as const

export function carryFilters(params: URLSearchParams): string {
  const next = new URLSearchParams()
  for (const name of SHARED_FILTERS) {
    const value = params.get(name)
    if (value) next.set(name, value)
  }
  const query = next.toString()
  return query ? `?${query}` : ''
}
