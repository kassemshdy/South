import { DoorCard } from '@/features/onboarding/DoorCard'
import { BROWSE_DOORS } from '@/features/onboarding/destinations'

/**
 * The three directories as full cards, for a section rather than a strip.
 *
 * The same array the popup and the directory switcher render — the homepage
 * previously carried a hand-written copy of this list under its own
 * `home.discoverHeading` section, and that copy is precisely the one that
 * drifted out of step with the hero.
 */
export function BrowseDoors() {
  return (
    <ul className="grid gap-4 sm:grid-cols-3">
      {BROWSE_DOORS.map((door) => (
        <li key={door.key}>
          <DoorCard door={door} />
        </li>
      ))}
    </ul>
  )
}
