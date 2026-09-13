import { AlertTriangle, ArrowLeft, Check, ShoppingBag, Store } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
import { DOOR_CARD, DoorBody } from '@/features/onboarding/DoorCard'
import { OFFER_DOORS, SEEK_DOORS, type Door } from '@/features/onboarding/destinations'
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
 * **Two levels, because the question has two levels.** Each half splits the
 * same way —— goods and products, or services and jobs —— so the fork is two
 * by two. Four leaves, reached in two taps rather than presented as four
 * choices at once: the audience here is someone who is not confident online,
 * and two large targets are easier than four.
 *
 * **And a notice stands between the second level and its page.** Every route
 * out of this widget ends at a dealing between two strangers, and the platform
 * checks only that the person listing is from the South —— it does not stand
 * behind the transaction. So the visitor reads that and presses agree before
 * the page opens, on both halves. It is asked every time rather than
 * remembered: the same reason the cards themselves carry no memory, and the
 * gate costs one tap at the point where it is actually relevant.
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
    doors: SEEK_DOORS,
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
  const [pending, setPending] = useState<Door | null>(null)
  const [expanded, setExpanded] = useState<Door | null>(null)

  // One step back per press, innermost screen first, so a visitor who went
  // two levels in and read the notice lands back on the doors rather than at
  // the top.
  const back = () => {
    if (expanded) {
      setExpanded(null)
      return
    }
    if (pending) {
      setPending(null)
      return
    }
    setIntent(null)
  }

  const branch = BRANCHES.find((candidate) => candidate.intent === intent) ?? null

  // Step three: the account explanation, for an anonymous visitor who chose to
  // list something. Shown before the phone-number prompt, never after it.
  if (expanded) {
    return (
      <div className="mx-auto w-full max-w-2xl rounded-2xl border-2 border-clay-200 bg-sand-50 p-6">
        <h3 className="text-lg font-bold">{t(expanded.titleKey)}</h3>
        <p className="mt-1 text-sm text-ink-500">{t('onboarding.stepsIntro')}</p>

        <ol className="mt-5 space-y-4">
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
          <Button type="button" variant="ghost" size="lg" onClick={back}>
            {t('onboarding.back')}
          </Button>
        </div>

        {/* Offered here, next to the steps, rather than after a failed
            attempt: someone who reads "register with your phone number" and
            decides it is not for them never reaches a later screen to be
            rescued on. */}
        <AssistedListing contextKey="assisted.contextHome" />
      </div>
    )
  }

  // Step two and a half: the notice, between a door and the page behind it.
  //
  // `needsAccount` decides what agreeing leads to, not whether the notice is
  // shown: an anonymous visitor who chose to list something still has the
  // steps panel ahead of them, so agreeing opens that rather than navigating.
  // Everyone else agrees straight onto the destination, and that control is a
  // real `<Link>` so it behaves like one.
  if (pending && branch) {
    const toSteps = branch.needsAccount && !isAuthenticated
    return (
      <div className="mx-auto w-full max-w-2xl rounded-2xl border-2 border-clay-300 bg-sand-50 p-6">
        <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clay-100 text-clay-700"
            aria-hidden="true"
          >
            <AlertTriangle className="h-5 w-5" />
          </span>
          {t('consent.heading')}
        </h3>

        {/* The notice is the screen, not a footnote on it: full size, full
            line height, nothing competing for the eye above the two
            controls. */}
        <p className="mt-4 leading-relaxed text-ink-700">{t('consent.body')}</p>

        <div className="mt-6 flex flex-wrap gap-3">
          {toSteps ? (
            <Button
              type="button"
              size="lg"
              onClick={() => {
                setExpanded(pending)
                setPending(null)
              }}
            >
              <Check className="h-5 w-5" aria-hidden="true" />
              {t('consent.agree')}
            </Button>
          ) : (
            <Button asChild size="lg">
              <Link to={pending.href}>
                <Check className="h-5 w-5" aria-hidden="true" />
                {t('consent.agree')}
              </Link>
            </Button>
          )}
          <Button type="button" variant="ghost" size="lg" onClick={back}>
            {t('onboarding.back')}
          </Button>
        </div>
      </div>
    )
  }

  // Step two: which kind, within the chosen intent.
  if (branch) {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <p className="text-center font-bold text-ink-900">{t(branch.titleKey)}</p>
        {/* Buttons rather than links, on both halves: the notice comes
            between a door and its page, so there is nothing here for a
            middle-click to open yet. The final control on the notice itself is
            a real link wherever it leads to a page. */}
        <ul className="mt-4 grid gap-4 sm:grid-cols-2">
          {branch.doors.map((door) => (
            <li key={door.key}>
              <button type="button" className={DOOR_CARD} onClick={() => setPending(door)}>
                <DoorBody door={door} />
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 text-center">
          <Button type="button" variant="ghost" onClick={back}>
            {t('onboarding.back')}
          </Button>
        </div>
      </div>
    )
  }

  // Step one: offering, or looking.
  //
  // Identical weight, because these are two halves of one question rather than
  // a call to action and its afterthought. No line of explanation under
  // either: it was answering a question nobody had yet asked.
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

      <ul className="mt-5 grid gap-4 sm:grid-cols-2">
        {BRANCHES.map((candidate) => {
          const Icon = candidate.icon
          return (
            <li key={candidate.intent}>
              <button
                type="button"
                onClick={() => setIntent(candidate.intent)}
                aria-expanded={false}
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
    </div>
  )
}
