import { DirectionProvider } from '@radix-ui/react-direction'
import * as Sentry from '@sentry/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from '@/App'
import { ToastProvider } from '@/components/ui/Toast'
import { AuthProvider } from '@/features/auth/AuthContext'
import { CartProvider } from '@/features/cart/CartContext'
import { FavouritesProvider } from '@/features/favourites/FavouritesContext'
import { activeLocale, I18nProvider, loadLocale, useI18n } from '@/i18n'
import { initAnalytics } from '@/services/analytics'
import { initClarity } from '@/services/clarity'
import { ApiError } from '@/services/api/client'
import '@/index.css'

// Inert in local dev unless VITE_SENTRY_DSN is set. Owner phone numbers, OTP
// codes and Arabic listing content never belong in error reports, so replay
// and default PII collection stay off rather than being scrubbed after the
// fact — see the security section in AGENTS.md.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    sendDefaultPii: false,
    integrations: [],
  })
}

// Same discipline as the DSN above: no measurement id, no script, no request.
initAnalytics()

// And the same again, with a harder gate. Clarity records the session rather
// than counting pages, and a recording cannot be un-started, so it refuses to
// load at all for anyone signed in or already on a private path — see
// services/clarity.ts for why that is the only place the decision can be made.
initClarity()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Never retry a client error — it will fail identically every time.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 2
      },
    },
  },
})

/** Radix needs the direction as a prop; `useI18n` is the one source for it. */
function RadixDirection({ children }: { children: ReactNode }) {
  const { dir } = useI18n()
  return <DirectionProvider dir={dir}>{children}</DirectionProvider>
}

const container = document.getElementById('root')
if (!container) throw new Error('Root element #root was not found')

// An English reader's catalog is fetched before the first paint rather than
// after it, so the page does not open in Arabic and then flip. For everybody
// else this resolves at once. If the fetch fails the site renders in Arabic.
void loadLocale(activeLocale())
  .catch(() => undefined)
  .then(() => {
    createRoot(container).render(
      <StrictMode>
        <I18nProvider>
          {/* DirectionProvider tells Radix primitives which way the UI runs, so
              popovers, selects and swipes behave correctly. It follows the chosen
              locale rather than being pinned to rtl: with a hardcoded direction,
              every Radix popover on the English site aligned and arrowed the wrong
              way, which the header's account menu made obvious. */}
          <RadixDirection>
            <QueryClientProvider client={queryClient}>
              <BrowserRouter>
                <AuthProvider>
                  <ToastProvider>
                    {/* Above the router so a cart survives navigation, and
                        inside ToastProvider so adding to it can confirm. */}
                    <CartProvider>
                      {/* Alongside the cart and for the same reason: a saved list
                          that did not survive navigation would not be a saved
                          list. Inside ToastProvider so saving can confirm. */}
                      <FavouritesProvider>
                        <App />
                      </FavouritesProvider>
                    </CartProvider>
                  </ToastProvider>
                </AuthProvider>
              </BrowserRouter>
            </QueryClientProvider>
          </RadixDirection>
        </I18nProvider>
      </StrictMode>,
    )
  })
