import { AlertTriangle, Check } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { ChoicePageShell } from '@/features/onboarding/ChoicePageShell'
import { DOOR_CARD, DoorBody } from '@/features/onboarding/DoorCard'
import { SEEK_DOORS } from '@/features/onboarding/destinations'
import { useScrollToStep } from '@/hooks/useScrollToStep'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/**
 * Looking for something: its own page, at `/browse`.
 *
 * The twin of `/offer`, with the same three doors: goods made in the South,
 * imported goods, and services and jobs. The two goods doors are one products
 * directory filtered on origin. The businesses directory is deliberately not
 * among them — see `destinations.ts`; it is reachable from the header and
 * from the switcher above each directory.
 *
 * **The responsibility notice is on this half too**, which it was not. It
 * used to be the offering half's alone, on the reasoning that browsing
 * carries no responsibility to accept — and that reasoning was wrong in the
 * way that matters. A dealing has two sides: the person buying is trusting a
 * stranger's description of a thing, and the platform stands behind that no
 * more than it stands behind the seller's half. So both sides read the same
 * warning before they start.
 *
 * What differs is only what is left out. The lister's copy carries clauses
 * that are theirs alone — what you publish is your responsibility, and a
 * proven legal violation removes you from the platform — and repeating those
 * at a buyer would be noise that teaches them to skip the box. `consent.body`
 * is the lister's, `consent.buyerBody` is this one, and the substance they
 * share is that the platform verifies only that the people listing are
 * southerners and guarantees nothing about the dealing itself.
 *
 * The doors behind the notice are real links, as they have always been: the
 * gate is the notice, and once it is answered there is nothing further
 * between a visitor and the directory they asked for.
 */
export function BrowsePage() {
  const t = useT()
  useSeo({
    title: `${t('browsePage.title')} | ${t('app.name')}`,
    description: t('browsePage.subtitle'),
  })

  // Asked every time rather than remembered, the same as the offering half.
  // A warning that shows once and then never again is a warning the tenth
  // visitor never reads.
  const [agreed, setAgreed] = useState(false)

  useScrollToStep(agreed ? 'doors' : 'notice')

  if (!agreed) {
    return (
      <ChoicePageShell title={t('consent.heading')} subtitle={t('browsePage.title')}>
        <div className="mx-auto max-w-2xl rounded-2xl border-2 border-clay-300 bg-white p-6 sm:p-8">
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-800"
            aria-hidden="true"
          >
            <AlertTriangle className="h-6 w-6" />
          </span>
          <p className="mt-5 leading-relaxed text-ink-700 sm:text-lg">
            {t('consent.buyerBody')}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button type="button" size="lg" onClick={() => setAgreed(true)}>
              <Check className="h-5 w-5" aria-hidden="true" />
              {t('consent.agree')}
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link to="/">{t('onboarding.back')}</Link>
            </Button>
          </div>
        </div>
      </ChoicePageShell>
    )
  }

  return (
    <ChoicePageShell title={t('browsePage.title')} subtitle={t('browsePage.subtitle')}>
      <div className="mx-auto max-w-3xl">
        <h2 className="text-lg font-bold text-ink-900">{t('browsePage.doorsTitle')}</h2>
        <ul className="mt-5 grid gap-4 sm:grid-cols-3">
          {SEEK_DOORS.map((door) => (
            <li key={door.key}>
              <Link to={door.href} className={DOOR_CARD}>
                <DoorBody door={door} />
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </ChoicePageShell>
  )
}
