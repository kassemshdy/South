import type { Breadcrumb, ErrorEvent } from '@sentry/react'

/**
 * Error reports carry URLs, and a URL's query string holds what somebody
 * typed into search (`?q=`) or the rounded position a directory sorted by
 * (`lat`, `lng`) -- neither may leave the browser, the same rule the backend
 * scrub and analytics follow. Everything after `?` is dropped, keeping the
 * path that says which page failed.
 */
export function withoutQuery(url: string): string {
  const cut = url.search(/[?#]/)
  return cut === -1 ? url : url.slice(0, cut)
}

export function scrubBreadcrumb(crumb: Breadcrumb): Breadcrumb {
  const data = crumb.data
  if (data) {
    for (const key of ['url', 'from', 'to']) {
      if (typeof data[key] === 'string') data[key] = withoutQuery(data[key] as string)
    }
  }
  return crumb
}

export function scrubEvent(event: ErrorEvent): ErrorEvent {
  if (event.request?.url) event.request.url = withoutQuery(event.request.url)
  if (event.request) delete event.request.query_string
  return event
}
