/**
 * Cloudflare Turnstile, on the two public registration forms.
 *
 * **Inert without `VITE_TURNSTILE_SITE_KEY`** — no script tag, no network
 * request, no widget, and `onToken(null)` so the form stays submittable. That
 * is the rule AGENTS.md states for every optional integration here, and it is
 * what lets the forms be developed, tested and demonstrated without a
 * Cloudflare account. The backend follows the same rule from the other side:
 * with no secret configured it verifies nothing, so an unprotected token and
 * no token at all are treated identically.
 *
 * The widget is not the check. A browser can be made to report any token it
 * likes; what counts is the server asking Cloudflare about it, in
 * `app/core/captcha.py`. This only obtains something for the server to ask
 * about.
 *
 * Remember that `VITE_` variables are inlined at build time here, so the key
 * has to be an `ARG`+`ENV` pair in `backend/Dockerfile` (the stage that builds
 * the bundle the API serves) as well as `frontend/Dockerfile` — setting it
 * only in the Railway dashboard leaves it undefined and the widget silently
 * absent.
 */

import { useEffect, useRef } from 'react'

import { activeLocale } from '@/i18n'

const SCRIPT_ID = 'cf-turnstile-script'
const SCRIPT_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'

interface TurnstileApi {
  render: (
    container: HTMLElement,
    options: {
      sitekey: string
      language: string
      callback: (token: string) => void
      'expired-callback': () => void
      'error-callback': () => void
    },
  ) => string
  remove: (widgetId: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

export function turnstileSiteKey(): string | undefined {
  return import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined
}

/** Loaded once per page, and only when a key exists. */
function loadScript(): Promise<void> {
  const existing = document.getElementById(SCRIPT_ID)
  if (existing) return Promise.resolve()

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('turnstile'))
    document.head.appendChild(script)
  })
}

interface TurnstileProps {
  /**
   * Called with the solved token, or with null whenever there is no usable
   * one — unconfigured, expired, or failed. The form reads it as "send this
   * along", never as "the visitor is verified".
   */
  onToken: (token: string | null) => void
}

export function Turnstile({ onToken }: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const siteKey = turnstileSiteKey()

  // Kept in a ref so re-renders of the parent never re-run the effect below;
  // rendering the widget twice would leave an orphan iframe behind.
  const onTokenRef = useRef(onToken)
  onTokenRef.current = onToken

  useEffect(() => {
    if (!siteKey) {
      onTokenRef.current(null)
      return
    }

    let widgetId: string | null = null
    let cancelled = false

    void loadScript()
      .then(() => {
        if (cancelled || !containerRef.current || !window.turnstile) return
        widgetId = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          language: activeLocale(),
          callback: (token) => onTokenRef.current(token),
          'expired-callback': () => onTokenRef.current(null),
          'error-callback': () => onTokenRef.current(null),
        })
      })
      .catch(() => {
        // Cloudflare unreachable. The server decides what that means: with a
        // secret configured it refuses the submission, which is the safer
        // failure and is asserted in the backend suite.
        if (!cancelled) onTokenRef.current(null)
      })

    return () => {
      cancelled = true
      if (widgetId && window.turnstile) window.turnstile.remove(widgetId)
    }
  }, [siteKey])

  if (!siteKey) return null
  return <div ref={containerRef} className="flex justify-center" />
}
