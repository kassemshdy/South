import { Briefcase, Building2, Package, Store, UserRound, Users } from 'lucide-react'

import type { TranslationKey } from '@/i18n'
import type { GoodsOrigin } from '@/types/api'

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
  /** Where someone who already has an account goes. */
  href: string
  /**
   * Where someone with no account goes, when that is somewhere else.
   *
   * Only the offering doors set it. There is no self-service sign-up here, so
   * an anonymous visitor cannot be sent to the wizard — they apply on a public
   * form, an administrator audits it, and the login arrives afterwards. A
   * signed-in owner adding a second listing must still land on the wizard, so
   * the two destinations have to coexist rather than one replacing the other.
   */
  applyHref?: string
}

/** The door's destination for this visitor. */
export function destinationFor(door: Door, isAuthenticated: boolean): string {
  return isAuthenticated ? door.href : (door.applyHref ?? door.href)
}

/**
 * The two directories the site links, as individual doors.
 *
 * Named separately rather than written inline in one array because more than
 * one surface offers them and they must be the same *objects*: sharing them is
 * what stops the lists from drifting the way the three hand-written copies of
 * this list once did.
 */
const productsDoor: Door = {
  key: 'products',
  icon: Package,
  // `/products`, not `/businesses`: someone who says they want to buy means
  // a thing with a price and an "add to order" button, not a list of shops
  // to work through.
  titleKey: 'onboarding.seekGoodsTitle',
  descriptionKey: 'onboarding.seekGoodsDescription',
  shortKey: 'browse.productsShort',
  href: '/products',
}

/**
 * Services and job applications: one door, «services and jobs», until the
 * owners split the talent directory in two. Each is now its own page.
 */
const servicesDoor: Door = {
  key: 'services',
  icon: Users,
  titleKey: 'onboarding.seekServicesTitle',
  descriptionKey: 'onboarding.seekServiceDescription',
  shortKey: 'browse.servicesShort',
  href: '/services',
}

const jobsDoor: Door = {
  key: 'jobs',
  icon: Briefcase,
  titleKey: 'onboarding.seekJobsTitle',
  descriptionKey: 'onboarding.seekJobsDescription',
  shortKey: 'browse.jobsShort',
  href: '/jobs',
}

/**
 * The switcher strip above each directory: goods and products, and services
 * and skills. The businesses tab was removed at the CEO's request -- the site
 * speaks only of those two -- so a shop is reached through its products.
 * `/businesses` still answers links already shared, but is linked from
 * nowhere.
 */
export const BROWSE_DOORS: Door[] = [productsDoor, servicesDoor, jobsDoor]

/**
 * Where someone looking for something goes: goods and products, or services.
 *
 * One goods door rather than the two it used to be (goods made in the South,
 * imported goods) and no jobs door: the owners' ticket of 29 Oct 2026 merged
 * the goods and moved jobs to a homepage door of their own, `JOBS_DOORS`.
 * A buyer narrows local or imported on the products directory itself, whose
 * origin filter and `/products/local` and `/products/imported` pages remain.
 *
 * The businesses directory is still not offered here: since the CEO asked for
 * the site to speak only of goods and products and of services and skills,
 * nothing else on the site names it either.
 */
export const SEEK_DOORS: Door[] = [productsDoor, servicesDoor]

/**
 * Where someone with something to offer can go: goods and products, or a
 * service -- the same two as `SEEK_DOORS`. Jobs have their own door since
 * the owners' ticket of 29 Oct 2026; see `JOBS_DOORS`.
 *
 * The split is the whole point: a business is a place or a product, a talent
 * profile is the person themselves. Collapsing them into one card is exactly
 * the bug that sent a craftsperson into the shop wizard.
 *
 * **Each of these has two destinations**, because the visitor decides which
 * one is right: `href` for somebody who already has an account, `applyHref`
 * for somebody who does not. Pointing both at the dashboard, which is what
 * this used to do, sent every new applicant to a login page they had no way
 * through — there is no self-service sign-up, so the anonymous route is the
 * public application form and nothing else. Pointing both at that form would
 * be the opposite mistake: an owner adding a second shop would be made to
 * apply for an account they already have.
 */
export const OFFER_DOORS: Door[] = [
  {
    // Goods and products, local or imported: one door since the owners'
    // ticket of 29 Oct 2026. The seller chooses which on the application form
    // itself (`BasicsForm`'s origin field), so the mark that keeps an import
    // off the "made in the South" shelf is still set, just one step later.
    key: 'business',
    icon: Store,
    titleKey: 'onboarding.seekGoodsTitle',
    descriptionKey: 'onboarding.offerGoodsDescription',
    shortKey: 'onboarding.ownerShort',
    href: '/dashboard/businesses/new',
    applyHref: '/register/business',
  },
  {
    // A talent profile listed under services.
    key: 'service',
    icon: UserRound,
    titleKey: 'onboarding.offerServiceTitle',
    descriptionKey: 'onboarding.talentDescription',
    shortKey: 'onboarding.talentShort',
    href: '/dashboard/talent?kind=SERVICE',
    applyHref: '/register/talent?kind=SERVICE',
  },
]

/**
 * The homepage's third door, "Jobs" (the owners' ticket, 29 Oct 2026): jobs
 * left the offering and looking halves for a page of their own, `/jobs-hub`,
 * with these three.
 *
 * Posting an offer and browsing the people looking for work are plain links.
 * Asking for a job means listing yourself, so it is a talent profile like a
 * service and takes the same two destinations: the public application for
 * somebody with no account, the dashboard for an owner who has one.
 */
export const JOBS_DOORS: Door[] = [
  {
    // An employer offering a job: one public form for everybody, signed in or
    // not, whose offer waits as a draft until a person publishes it.
    key: 'employer',
    icon: Building2,
    titleKey: 'jobsHub.postTitle',
    descriptionKey: 'onboarding.offerEmployerDescription',
    shortKey: 'onboarding.offerEmployerShort',
    href: '/vacancies/offer',
  },
  {
    key: 'seekers',
    icon: Users,
    titleKey: 'jobsHub.seekersTitle',
    descriptionKey: 'onboarding.seekJobsDescription',
    shortKey: 'browse.jobsShort',
    href: '/jobs',
  },
  {
    key: 'job',
    icon: Briefcase,
    titleKey: 'jobsHub.applyTitle',
    descriptionKey: 'onboarding.offerJobDescription',
    shortKey: 'onboarding.offerJobShort',
    href: '/dashboard/talent?kind=JOB_SEEKER',
    applyHref: '/register/talent?kind=JOB_SEEKER',
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

/**
 * The `?origin=` a goods door carries, or undefined for anything else.
 *
 * Checked against the two known values rather than cast, so a hand-edited
 * URL starts the form local instead of sending the API a value it refuses.
 */
export function originFromParams(params: URLSearchParams): GoodsOrigin | undefined {
  const value = params.get('origin')
  return value === 'LOCAL' || value === 'IMPORTED' ? value : undefined
}
