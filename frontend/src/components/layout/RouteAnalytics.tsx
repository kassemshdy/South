import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

import { trackPageView } from '@/services/analytics'

/**
 * Reports one page view per route, including the first.
 *
 * A single-page app never reloads, so the tag's own automatic page view fires
 * once and then never again — which would report one visit per session and
 * nothing at all about where anyone actually went. This sits next to
 * `ScrollToTop`, which exists for the same reason: things the browser does for
 * free on a normal site have to be done by hand here.
 *
 * Renders nothing, and does nothing at all when no measurement id is
 * configured — see `services/analytics.ts`.
 */
export function RouteAnalytics() {
  const { pathname } = useLocation()

  useEffect(() => {
    // The title is set by `useSeo` in an effect too, and effects run child
    // first: reading it on the next frame gets the title of the page we are
    // on rather than the one we just left.
    const frame = window.requestAnimationFrame(() => {
      trackPageView(pathname, document.title)
    })
    return () => window.cancelAnimationFrame(frame)
  }, [pathname])

  return null
}
