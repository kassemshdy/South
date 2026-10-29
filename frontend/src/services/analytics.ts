/**
 * Page-view analytics, so "which pages do people engage with" stops being a
 * guess.
 *
 * Wired the way Sentry is wired (`main.tsx`, and Error Tracking in
 * `AGENTS.md`): a `VITE_`-prefixed variable set per service in Railway, and
 * **completely inert without it**. No id means no script tag, no network
 * request, no measurement — so local development and the test suite never
 * phone home and never pollute the numbers with a developer's own clicks.
 *
 * Two rules about what leaves the browser:
 *
 * **The query string is dropped.** `?q=…` on the directory carries whatever
 * someone typed to find a business, which can be a person's name or their own
 * shop. `AGENTS.md` forbids owner-authentication data reaching Sentry; the
 * same instinct applies to anything sent anywhere, and a page path answers the
 * question we actually asked without it.
 *
 * **Nothing is sent that names someone.** A signed-in account is reported
 * only by its opaque id and its type (owner or staff) -- never a name, phone
 * number or email, which Google's terms forbid in Analytics anyway (the
 * owners' request for per-user reporting, 29 Oct 2026). A visitor who is not
 * signed in is not identified at all.
 *
 * **Contact clicks and listing context are events.** A click on a WhatsApp,
 * phone, email, social or map link is reported as `contact_click` with the
 * kind of link and its domain only -- never the number, the prefilled
 * message or the full URL. Listing and directory pages report their
 * classification (type, category, town, skill) so it can be used as custom
 * dimensions; a search term never is.
 *
 * And the private areas are not measured at all. `/dashboard` and `/admin`
 * are an owner's own workspace and the team's moderation queue — `robots.txt`
 * already declares them off limits, and counting our own moderation clicks
 * would corrupt the one question this exists to answer.
 */

const MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID as string | undefined

type GtagArgs =
  | [command: 'js', at: Date]
  | [command: 'config', id: string, params?: Record<string, unknown>]
  | [command: 'event', name: string, params?: Record<string, unknown>]
  | [command: 'set', params: Record<string, unknown>]

declare global {
  interface Window {
    dataLayer?: unknown[]
    gtag?: (...args: GtagArgs) => void
  }
}

/** True only when an id is configured — every caller checks this first. */
export const analyticsEnabled = Boolean(MEASUREMENT_ID)

/** Paths whose views are never reported. See the note above. */
const PRIVATE_PREFIXES = ['/dashboard', '/admin'] as const

let started = false

/**
 * Load the tag once, if configured.
 *
 * `send_page_view: false` because this is a single-page app: the tag's own
 * automatic page view fires once on load and then never again, which would
 * report one visit per session and nothing about where anyone went.
 * `trackPageView` below is called per route instead.
 */
export function initAnalytics(): void {
  if (!MEASUREMENT_ID || started || typeof document === 'undefined') return
  started = true

  const script = document.createElement('script')
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`
  document.head.appendChild(script)

  window.dataLayer = window.dataLayer ?? []
  // `arguments`, not a rest array, exactly as Google's own snippet does:
  // gtag.js only acts on queued Arguments objects and silently skips plain
  // arrays. With `(...args) => push(args)` the tag loaded but the config and
  // every page view were dropped, so GA showed no data at all.
  window.gtag = function gtag(..._args: GtagArgs) {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer?.push(arguments)
  }
  window.gtag('js', new Date())
  window.gtag('config', MEASUREMENT_ID, {
    send_page_view: false,
    anonymize_ip: true,
  })
  document.addEventListener('click', onDocumentClick, true)
}

function isPrivatePath(path: string = window.location.pathname): boolean {
  return PRIVATE_PREFIXES.some((prefix) => path.startsWith(prefix))
}

function send(name: string, params: Record<string, unknown>): void {
  if (!MEASUREMENT_ID || !window.gtag || isPrivatePath()) return
  window.gtag('event', name, params)
}

/** A listing's classification, as custom-dimension-ready parameters. */
export interface ListingContext {
  listing_type: 'business' | 'product' | 'service' | 'job_seeker'
  listing: string
  category?: string | null
  location?: string | null
  skill?: string | null
  shop?: string | null
}

/**
 * The listing on screen, carried on its contact clicks -- only while the
 * path it was set on is still the one shown, so a click on the next page is
 * never credited to the last listing.
 */
let pageContext: { path: string; params: Record<string, string> } | null = null

function clean(params: object): Record<string, string> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== ''),
  ) as Record<string, string>
}

/** One view of a shop, product or profile page, with its classification. */
export function trackListingView(context: ListingContext): void {
  const params = clean(context)
  pageContext = { path: window.location.pathname, params }
  send('listing_view', params)
}

/** The filters a directory is showing (never the search text). */
export function trackDirectoryView(params: {
  directory: string
  category?: string
  location?: string
  skill?: string
  origin?: string
  displaced?: boolean
}): void {
  send('directory_view', clean({ ...params, displaced: params.displaced ? 'yes' : '' }))
}

/** Who is signed in, by opaque id and type only; null when signed out. */
export function setAnalyticsUser(user: { id: string; role: string } | null): void {
  if (!MEASUREMENT_ID || !window.gtag) return
  window.gtag('set', {
    user_id: user?.id ?? null,
    user_properties: { user_type: user ? user.role.toLowerCase() : 'visitor' },
  })
}

const SOCIAL_HOSTS: Record<string, string> = {
  'instagram.com': 'instagram',
  'facebook.com': 'facebook',
  'fb.com': 'facebook',
  'tiktok.com': 'tiktok',
  'youtube.com': 'youtube',
  'youtu.be': 'youtube',
  'x.com': 'x',
  'twitter.com': 'x',
  'linkedin.com': 'linkedin',
  't.me': 'telegram',
}

/** The kind of a contact or outbound link, or null for an internal one. */
export function contactMethod(href: string): { method: string; domain: string } | null {
  if (href.startsWith('tel:')) return { method: 'phone', domain: '' }
  if (href.startsWith('mailto:')) return { method: 'email', domain: '' }
  let url: URL
  try {
    url = new URL(href, window.location.href)
  } catch {
    return null
  }
  if (url.origin === window.location.origin) return null
  const host = url.hostname.replace(/^www\./, '')
  if (host === 'wa.me' || host.endsWith('whatsapp.com')) return { method: 'whatsapp', domain: host }
  if (host.includes('google.') && url.pathname.startsWith('/maps')) return { method: 'maps', domain: host }
  if (host === 'maps.google.com' || host === 'maps.app.goo.gl') return { method: 'maps', domain: host }
  const social = Object.entries(SOCIAL_HOSTS).find(([domain]) => host === domain || host.endsWith(`.${domain}`))
  if (social) return { method: social[1], domain: host }
  return { method: 'external', domain: host }
}

function onDocumentClick(event: MouseEvent): void {
  const target = event.target as Element | null
  const link = target?.closest?.('a[href]') as HTMLAnchorElement | null
  if (!link) return
  const kind = contactMethod(link.getAttribute('href') ?? '')
  if (!kind) return
  const listing = pageContext?.path === window.location.pathname ? pageContext.params : {}
  send('contact_click', clean({ contact_method: kind.method, link_domain: kind.domain, ...listing }))
}

/**
 * Record one page view.
 *
 * `path` should be a pathname only. The caller passes `location.pathname`, and
 * this drops anything after `?` or `#` regardless, because the rule matters
 * more than the discipline of every future caller.
 */
export function trackPageView(path: string, title?: string): void {
  if (!MEASUREMENT_ID || !window.gtag) return

  const pathOnly = path.split(/[?#]/)[0] ?? path
  if (isPrivatePath(pathOnly)) return

  window.gtag('event', 'page_view', {
    page_path: pathOnly,
    page_title: title,
  })
}
