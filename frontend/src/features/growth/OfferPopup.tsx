import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useAuth } from '@/features/auth/AuthContext'
import { OfferText } from '@/features/growth/OfferText'
import { useT } from '@/i18n'
import { siteSettingsApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

const DISMISSED_KEY = 'south.offerPopupDismissed'
/** Long enough to have looked at the page first. */
const DELAY_MS = 5_000

/** Where the offer would be in the way, or is the page already. */
const QUIET_PATHS = ['/admin', '/dashboard', '/offer', '/register', '/login', '/account']

function dismissed(): boolean {
  try {
    return window.localStorage.getItem(DISMISSED_KEY) !== null
  } catch {
    // No storage, no memory of a close: don't show it at all rather than
    // show it on every page.
    return true
  }
}

function dismiss() {
  try {
    window.localStorage.setItem(DISMISSED_KEY, new Date().toISOString())
  } catch {
    // Nothing to remember it in; it stays closed for this page.
  }
}

/**
 * The offer to sellers, once, to a visitor who is not signed in (the owners'
 * request, 29 Oct 2026). Closed, it never comes back in that browser. Off
 * until the manager switches it on at the growth page; the wording is the
 * same offer they edit there.
 */
export function OfferPopup() {
  const t = useT()
  const { isAuthenticated } = useAuth()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const quiet = isAuthenticated || QUIET_PATHS.some((path) => pathname.startsWith(path))
  const popup = useQuery({
    queryKey: queryKeys.offerPopup,
    queryFn: siteSettingsApi.offerPopup,
    enabled: !quiet && !dismissed(),
    staleTime: 10 * 60_000,
  })

  useEffect(() => {
    if (quiet || !popup.data?.enabled || dismissed()) return
    const timer = window.setTimeout(() => setOpen(true), DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [quiet, popup.data?.enabled])

  if (!popup.data?.enabled) return null

  const close = () => {
    dismiss()
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <DialogContent title={t('growth.offerHeading')} className="max-w-xl">
        <OfferText text={popup.data.offer ?? t('growth.offerDefault')} className="text-[15px]" />
        <div className="mt-5 flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/offer" onClick={close}>
              {t('nav.offer')}
            </Link>
          </Button>
          <Button variant="ghost" onClick={close}>
            {t('common.close')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
