import { DoorStrip } from '@/features/onboarding/DoorStrip'
import { OFFER_DOORS } from '@/features/onboarding/destinations'

/**
 * A business, or a talent profile — the same fork the popup offers, at the
 * top of the two forms it leads to.
 *
 * Someone who picked wrong finds out here, on the form, not on the homepage:
 * a carpenter who took the `onboarding.ownerTitle` door meets a wizard
 * asking for an address and opening hours, and until now the only way
 * across was back to the homepage and through the popup again.
 *
 * On the business wizard this must only be rendered **before the first save**
 * — the wizard writes a DRAFT listing once step one is done, and offering to
 * walk away after that leaves a stub behind. `BusinessWizardPage` guards it
 * on `businessId === null`.
 */
export function OfferSwitcher({ current }: { current: 'business' | 'imported' | 'talent' }) {
  return (
    <DoorStrip doors={OFFER_DOORS} current={current} label="onboarding.offerSwitcherLabel" />
  )
}
