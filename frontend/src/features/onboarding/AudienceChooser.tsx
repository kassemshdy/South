import { ArrowLeft, Check, ShoppingBag, Store } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
import { DOOR_CARD, DoorBody, DoorCard } from '@/features/onboarding/DoorCard'
import { BROWSE_DOORS, OFFER_DOORS, type Door } from '@/features/onboarding/destinations'
import { useT, type TranslationKey } from '@/i18n'

/**
 * The one question the homepage asks: are you offering, or are you looking?
 *
 * It started as a first-visit question that remembered its answer and then got
 * out of the way. That was the wrong instinct for this site: these cards *are*
 * the homepage's navigation for people who are not confident online, and
 * something you only see once cannot be navigation. So it is permanent, and it
 * carries no dismissal and no memory.
 *
 * **Two levels, because the question has two levels.** Offering splits into a
 * business and a personal craft; looking splits into goods and someone
 * skilled. Four leaves, reached in two taps rather than presented as four
 * choices at once — the audience here is someone who is not confident online,
 * and two large targets are easier than four.
 *
 * **And it is one widget now, which it was not.** The homepage used to ask
 * this three separate times: this chooser, a pair of cards in the hero, and a
 * third "what are you looking for" section below. The three disagreed --
 * "I want to buy" led to `/products` in one and `/businesses` in another, and
 * the hero's offer card sent a carpenter to the *business* wizard because it
 * collapsed goods and crafts into one card. The hero's own comment already
 * said the page "asks it first and asks it once", so the duplication was a
 * drift from the stated intent rather than a decision. This is that one
 * asking, and it lives where the hero pair used to.
 *
 * For a visitor who is not signed in, choosing to list something does not jump
 * straight to a phone-number prompt: it opens the steps involved first, in
 * place, because "sign in" as an answer to "I have a shop" tells you nothing
 * about what you are agreeing to. Someone already signed in has been through
 * that, so their cards go straight to the real destination.
 */

type Intent = 'offer' | 'seek'

interface Branch {
  intent: Intent
  icon: typeof Store
  titleKey: TranslationKey
  /** Listing anything needs an account; looking at anything does not. */
  needsAccount: boolean
  doors: Door[]
}

/**
 * The two halves, and what is behind each.
 *
 * The doors themselves live in `destinations.ts` and are shared with the
 * switcher above every directory and the strip further down the homepage.
 * They used to be written out here, and in two other components, and the
 * three drifted until they contradicted each other —— see that file.
 */
const BRANCHES: Branch[] = [
  {
    intent: 'offer',
    icon: Store,
    titleKey: 'home.actionOffer',
    needsAccount: true,
    doors: OFFER_DOORS,
  },
  {
    intent: 'seek',
    icon: ShoppingBag,
    titleKey: 'home.actionBrowse',
    needsAccount: false,
    doors: BROWSE_DOORS,
  },
]

const STEP_KEYS: TranslationKey[] = [
  'onboarding.step1',
  'onboarding.step2',
  'onboarding.step3',
]

export function AudienceChooser({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const t = useT()
  const [intent, setIntent] = useState<Intent | null>(null)
  const [expanded, setExpanded] = useState<Door | null>(null)

  const branch = BRANCHES.find((candidate) => candidate.intent === intent) ?? null

  /** Closing the dialog puts the widget back to its one question. */
  const close = () => {
    setIntent(null)
    setExpanded(null)
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      {/* The question is asked out loud rather than implied by two cards.
          Modest weight: the hero's own headline says what the site is, and
          this labels the choice under it without competing. */}
      <h2 className="text-center text-lg font-bold text-ink-900">
        {t('onboarding.heading')}
      </h2>
      <p className="mx-auto mt-1 max-w-md text-center text-sm text-ink-500">
        {t('onboarding.subtitle')}
      </p>

      {/* Step one: offering, or looking.
          Identical weight, because these are two halves of one question
          rather than a call to action and its afterthought. No line of
          explanation under either: it was answering a question nobody had
          yet asked. */}
      <ul className="mt-5 grid gap-4 sm:grid-cols-2">
        {BRANCHES.map((candidate) => {
          const Icon = candidate.icon
          return (
            <li key={candidate.intent}>
              <button
                type="button"
                onClick={() => setIntent(candidate.intent)}
                aria-haspopup="dialog"
                className="group flex h-full w-full flex-col items-center gap-3 rounded-2xl border-2 border-ink-100 bg-white p-6 text-center shadow-card transition-all hover:-translate-y-0.5 hover:border-clay-300 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-sand-100 text-clay-600 transition-colors group-hover:bg-clay-500 group-hover:text-white">
                  <Icon className="h-6 w-6" aria-hidden="true" />
                </span>
                <span className="text-lg font-bold leading-snug text-ink-900">
                  {t(candidate.titleKey)}
                </span>
                <span className="flex items-center gap-1.5 text-sm font-semibold text-clay-600">
                  {t('onboarding.choose')}
                  <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      {/* Step two, and step three behind it, in a dialog rather than in place.
          The second level used to replace the two cards where they stood,
          which read as the page having changed under you —— and it left the
          homepage's own heading describing something that was no longer
          there. A dialog says "this is a decision, and you can back out of
          it", which is what it is. Closing returns to the one question. */}
      <Dialog open={branch !== null} onOpenChange={(open) => (open ? null : close())}>
        {branch ? (
          <DialogContent
            title={t(expanded ? expanded.titleKey : branch.titleKey)}
            description={expanded ? t('onboarding.stepsIntro') : t('onboarding.subtitle')}
          >
            {expanded ? (
              // Step three: the account explanation, for an anonymous visitor
              // who chose to list something. Shown before the phone-number
              // prompt, never after it.
              <>
                <ol className="space-y-4">
                  {STEP_KEYS.map((key, index) => (
                    <li key={key} className="flex items-start gap-3">
                      <span
                        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-clay-500 text-sm font-bold text-white ltr-nums"
                        aria-hidden="true"
                      >
                        {index + 1}
                      </span>
                      <span className="leading-relaxed text-ink-700">{t(key)}</span>
                    </li>
                  ))}
                </ol>

                <div className="mt-6 flex flex-wrap gap-3">
                  <Button asChild size="lg">
                    <Link to="/login">
                      <Check className="h-5 w-5" aria-hidden="true" />
                      {t('onboarding.start')}
                    </Link>
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="lg"
                    onClick={() => setExpanded(null)}
                  >
                    {t('onboarding.back')}
                  </Button>
                </div>

                {/* Offered here, next to the steps, rather than after a failed
                    attempt: someone who reads "register with your phone
                    number" and decides it is not for them never reaches a
                    later screen to be rescued on. */}
                <AssistedListing contextKey="assisted.contextHome" />
              </>
            ) : (
              <ul className="grid gap-4 sm:grid-cols-2">
                {branch.doors.map((door) => (
                  <li key={door.key}>
                    {branch.needsAccount && !isAuthenticated ? (
                      <button
                        type="button"
                        className={DOOR_CARD}
                        onClick={() => setExpanded(door)}
                      >
                        <DoorBody door={door} />
                      </button>
                    ) : (
                      <DoorCard door={door} onNavigate={close} />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  )
}
