import { ArrowLeft, Check, Search, ShoppingBag, Store, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
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

interface Leaf {
  key: string
  icon: typeof Store
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  /** Set for the paths that need an account; the rest navigate straight away. */
  needsAccount: boolean
  href: string
}

interface Branch {
  intent: Intent
  icon: typeof Store
  titleKey: TranslationKey
  leaves: Leaf[]
}

const BRANCHES: Branch[] = [
  {
    intent: 'offer',
    icon: Store,
    titleKey: 'home.actionOffer',
    leaves: [
      {
        key: 'business',
        icon: Store,
        titleKey: 'onboarding.ownerTitle',
        descriptionKey: 'onboarding.ownerDescription',
        needsAccount: true,
        href: '/dashboard/businesses/new',
      },
      {
        key: 'talent',
        icon: UserRound,
        titleKey: 'onboarding.talentTitle',
        descriptionKey: 'onboarding.talentDescription',
        needsAccount: true,
        href: '/dashboard/talent',
      },
    ],
  },
  {
    intent: 'seek',
    icon: ShoppingBag,
    titleKey: 'home.actionBrowse',
    leaves: [
      {
        key: 'goods',
        icon: ShoppingBag,
        titleKey: 'onboarding.seekGoodsTitle',
        descriptionKey: 'onboarding.seekGoodsDescription',
        needsAccount: false,
        // `/products`, not `/businesses`: someone who says they want to buy
        // means a thing with a price and an "add to order" button, not a list
        // of shops to work through.
        href: '/products',
      },
      {
        key: 'service',
        icon: Search,
        titleKey: 'onboarding.seekServiceTitle',
        descriptionKey: 'onboarding.seekServiceDescription',
        needsAccount: false,
        href: '/talent',
      },
    ],
  },
]

const STEP_KEYS: TranslationKey[] = [
  'onboarding.step1',
  'onboarding.step2',
  'onboarding.step3',
]

/** A whole-card target, sized for a thumb rather than a cursor. */
const CARD =
  'group flex h-full w-full flex-row items-center gap-4 rounded-2xl border-2 border-ink-100 bg-white p-5 text-start shadow-card transition-colors hover:border-clay-300 hover:bg-sand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2 sm:flex-col sm:items-start sm:gap-0 sm:p-6'

export function AudienceChooser({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const t = useT()
  const [intent, setIntent] = useState<Intent | null>(null)
  const [expanded, setExpanded] = useState<Leaf | null>(null)

  const back = () => {
    if (expanded) {
      setExpanded(null)
      return
    }
    setIntent(null)
  }

  const branch = BRANCHES.find((candidate) => candidate.intent === intent) ?? null

  const Body = ({ leaf }: { leaf: Leaf }) => {
    const Icon = leaf.icon
    return (
      <>
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-sand-100 text-clay-600 transition-colors group-hover:bg-clay-500 group-hover:text-white sm:h-14 sm:w-14">
          <Icon className="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-bold text-ink-900 sm:mt-4 sm:text-lg">
            {t(leaf.titleKey)}
          </span>
          <span className="mt-1 block text-sm leading-relaxed text-ink-500">
            {t(leaf.descriptionKey)}
          </span>
          <span className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-clay-600 sm:mt-4">
            {t('onboarding.choose')}
            <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
          </span>
        </span>
      </>
    )
  }

  // Step three: the account explanation, for an anonymous visitor who chose to
  // list something.
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

  // Step two: which kind, within the chosen intent.
  if (branch) {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <p className="text-center font-bold text-ink-900">{t(branch.titleKey)}</p>
        <ul className="mt-4 grid gap-4 sm:grid-cols-2">
          {branch.leaves.map((leaf) => (
            <li key={leaf.key}>
              {leaf.needsAccount && !isAuthenticated ? (
                <button
                  type="button"
                  className={CARD}
                  onClick={() => setExpanded(leaf)}
                  aria-expanded={false}
                >
                  <Body leaf={leaf} />
                </button>
              ) : (
                <Link to={leaf.href} className={CARD}>
                  <Body leaf={leaf} />
                </Link>
              )}
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
