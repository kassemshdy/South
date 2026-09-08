import { DirectionProvider } from '@radix-ui/react-direction'
import * as Sentry from '@sentry/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from '@/App'
import { ToastProvider } from '@/components/ui/Toast'
import { AuthProvider } from '@/features/auth/AuthContext'
import { I18nProvider, useI18n } from '@/i18n'
import { initAnalytics } from '@/services/analytics'
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
                <App />
              </ToastProvider>
            </AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </RadixDirection>
    </I18nProvider>
  </StrictMode>,
)
