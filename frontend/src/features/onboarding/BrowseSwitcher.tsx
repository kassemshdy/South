import { useSearchParams } from 'react-router-dom'

import { DoorStrip } from '@/features/onboarding/DoorStrip'
import { BROWSE_DOORS, carryFilters, type BrowseKey } from '@/features/onboarding/destinations'

/**
 * The three directories, as a row you can hop between.
 *
 * The three used to be islands: a visitor who searched the products
 * directory and found nothing had no way across to the shops or the
 * craftspeople except the browser's back button and the homepage. So the
 * same three doors the popup offers are repeated at the top of each
 * directory, where the decision is actually being reconsidered.
 *
 * It renders `BROWSE_DOORS`, so it cannot drift from the popup that sent the
 * visitor here — which is the failure this whole rework is undoing.
 *
 * **What travels across:** `q` and `location`, and only those. See
 * `SHARED_FILTERS` for why the rest are dropped rather than carried into a
 * page that cannot show or clear them.
 */
export function BrowseSwitcher({ current }: { current: BrowseKey }) {
  const [searchParams] = useSearchParams()

  return (
    <DoorStrip
      doors={BROWSE_DOORS}
      current={current}
      label="browse.switcherLabel"
      suffix={carryFilters(searchParams)}
    />
  )
}
