import { Link } from 'react-router-dom'

import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'
import type { Door } from '@/features/onboarding/destinations'

/**
 * A row of doors with the current one marked — the compact form of the same
 * choice the popup presents as cards.
 *
 * Generic over which set of doors, because both halves of the site need it:
 * the three directories a visitor moves between, and the two things an owner
 * can add. One renderer so the two cannot end up looking like different
 * controls that happen to do the same job.
 */
export function DoorStrip({
  doors,
  current,
  label,
  suffix = '',
}: {
  doors: Door[]
  /**
   * The door the caller is currently on, marked and announced. Omitted on the
   * homepage, where none of the three is where you are.
   */
  current?: string
  label: TranslationKey
  /** Appended to every href — the query string a directory hop carries. */
  suffix?: string
}) {
  const t = useT()

  return (
    <nav aria-label={t(label)} className="mb-6">
      {/* One scrolling row rather than a wrapping block. Three Arabic labels
          do not fit a 420px phone, and wrapped pills read as a stray group of
          buttons; a row that runs off the edge reads as tabs, which is what
          this is. Same pattern as the dashboard's own tab strip. */}
      <ul className="-mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-1">
        {doors.map((door) => {
          const Icon = door.icon
          const here = door.key === current
          return (
            <li key={door.key}>
              <Link
                to={`${door.href}${suffix}`}
                // `aria-current` rather than colour alone: the marked entry
                // has to be announced, not merely look different.
                aria-current={here ? 'page' : undefined}
                className={cn(
                  'inline-flex shrink-0 snap-start items-center gap-2 whitespace-nowrap rounded-xl border-2 px-4 py-2.5 text-sm font-semibold transition-colors',
                  here
                    ? 'border-brand-800 bg-brand-800 text-white'
                    : 'border-ink-100 bg-white text-ink-700 hover:border-brand-300 hover:bg-sand-50',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {t(door.shortKey)}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
