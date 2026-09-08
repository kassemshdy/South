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
 * **Nothing is sent about who someone is.** No user id, no phone number, no
 * listing ownership. This measures pages, not people.
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
  window.gtag = function gtag(...args: GtagArgs) {
    window.dataLayer?.push(args)
  }
  window.gtag('js', new Date())
  window.gtag('config', MEASUREMENT_ID, {
    send_page_view: false,
    anonymize_ip: true,
  })
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
  if (PRIVATE_PREFIXES.some((prefix) => pathOnly.startsWith(prefix))) return

  window.gtag('event', 'page_view', {
    page_path: pathOnly,
    page_title: title,
  })
}
