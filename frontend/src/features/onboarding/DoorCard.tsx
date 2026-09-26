import { ArrowLeft } from 'lucide-react'

import { useT } from '@/i18n'
import type { Door } from '@/features/onboarding/destinations'

/**
 * A whole-card target, sized for a thumb rather than a cursor.
 *
 * Skin and contents are separate exports because the element around them is
 * the caller's to choose: a `<button>` where a responsibility notice has to
 * sit between the door and its page (offering something), or a `<Link>`
 * straight through where it does not (browsing). `doorCard` returns plain
 * classes rather than a wrapping element for exactly that reason -- the
 * caller applies it to whichever tag the door actually needs. The strip above
 * each directory renders its own links, independently, from `DoorStrip`.
 *
 * **Each page is in its homepage colour**, the CEO's choice: every door on
 * `/offer` is the olive green of the homepage's offering card, every door on
 * `/browse` the terracotta of its looking card. The colour a visitor pressed
 * on the homepage is the colour of the page they land on, so the choice they
 * made stays visible on the next screen. See `AudienceChooser` for the pair.
 */
export type DoorSide = 'offer' | 'browse'

const SURFACE: Record<DoorSide, string> = {
  offer: 'from-brand-600 to-brand-800',
  browse: 'from-clay-500 to-clay-700',
}

export function doorCard(side: DoorSide): string {
  return `group relative isolate flex h-full w-full flex-row items-center gap-4 overflow-hidden rounded-2xl bg-gradient-to-br ${SURFACE[side]} p-5 text-start shadow-lift transition-all duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-wheat-500 focus-visible:ring-offset-2 sm:flex-col sm:items-start sm:gap-0 sm:p-6`
}

export function DoorBody({ door }: { door: Door }) {
  const t = useT()
  const Icon = door.icon
  return (
    <>
      {/* A soft disc of light for depth, as on the homepage cards. */}
      <span aria-hidden="true" className="absolute -end-8 -top-8 -z-10 h-32 w-32 rounded-full bg-white/10" />
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white text-ink-900 shadow-md sm:h-14 sm:w-14">
        <Icon className="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-bold text-white sm:mt-4 sm:text-lg">{t(door.titleKey)}</span>
        <span className="mt-1 block text-sm leading-relaxed text-white/85">
          {t(door.descriptionKey)}
        </span>
        <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white px-4 py-1.5 text-sm font-bold text-ink-900 sm:mt-4">
          {t('onboarding.choose')}
          <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
        </span>
      </span>
    </>
  )
}
