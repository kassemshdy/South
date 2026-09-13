import { ArrowLeft } from 'lucide-react'

import { useT } from '@/i18n'
import type { Door } from '@/features/onboarding/destinations'

/**
 * A whole-card target, sized for a thumb rather than a cursor.
 *
 * Skin and contents are separate exports because the element around them is
 * the caller's to choose. Every door in the chooser is now a `<button>` —— the
 * responsibility notice sits between a door and its page, so there is no
 * navigation to hand a link yet —— and this file used to also ship a `<Link>`
 * flavour for the doors that went straight through. Nothing needs it now, so
 * it is gone rather than left exported and unused; the strip renders its own
 * links from `DoorStrip`.
 */
export const DOOR_CARD =
  'group flex h-full w-full flex-row items-center gap-4 rounded-2xl border-2 border-ink-100 bg-white p-5 text-start shadow-card transition-colors hover:border-clay-300 hover:bg-sand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2 sm:flex-col sm:items-start sm:gap-0 sm:p-6'

export function DoorBody({ door }: { door: Door }) {
  const t = useT()
  const Icon = door.icon
  return (
    <>
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-sand-100 text-clay-600 transition-colors group-hover:bg-clay-500 group-hover:text-white sm:h-14 sm:w-14">
        <Icon className="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-bold text-ink-900 sm:mt-4 sm:text-lg">
          {t(door.titleKey)}
        </span>
        <span className="mt-1 block text-sm leading-relaxed text-ink-500">
          {t(door.descriptionKey)}
        </span>
        <span className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-clay-600 sm:mt-4">
          {t('onboarding.choose')}
          <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
        </span>
      </span>
    </>
  )
}
