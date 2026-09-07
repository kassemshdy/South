import { ArrowLeft, Check, Search, Store, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useT, type TranslationKey } from '@/i18n'

/**
 * The first question the site asks: which half of it is yours.
 *
 * The homepage already triages *browsing* three ways further down. What was
 * missing is the split before that — an owner had to work out for themselves
 * that a header link was their way in. This is written for someone who is not
 * confident online: three large targets, one short line each, no jargon.
 *
 * Two rules it must not break. It is **never a wall**: everything below stays
 * reachable without answering, and skipping is one tap. And it is asked
 * **once** — the answer is remembered, so a returning visitor gets the site,
 * not the question again.
 *
 * Choosing to list something does not jump straight to a phone-number prompt.
 * It opens the three steps involved first, in place, because "sign in" as an
 * answer to "I have a shop" tells you nothing about what you are agreeing to.
 */

const STORAGE_KEY = 'south.audience'

type Audience = 'owner' | 'talent' | 'visitor'

/**
 * What we store is "this has been answered", and skipping counts.
 *
 * Reading back only the three audiences would let the dismissal fall through
 * the type guard and re-ask the question on the next visit — which is exactly
 * the nag this component is supposed not to be. The specific answer is kept
 * rather than a bare flag because it is the one signal we have about who is
 * arriving, and it costs nothing to keep.
 */
type Answer = Audience | 'dismissed'

const ANSWERS: readonly Answer[] = ['owner', 'talent', 'visitor', 'dismissed']

function readAnswer(): Answer | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null && (ANSWERS as readonly string[]).includes(stored)) {
      return stored as Answer
    }
  } catch {
    // Private browsing can throw on storage access; asking again is harmless.
  }
  return null
}

function remember(answer: Answer): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, answer)
  } catch {
    // Non-fatal: the question simply comes back next visit.
  }
}

interface Choice {
  audience: Audience
  icon: typeof Store
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  /** Set for the paths that need an account; the rest navigate straight away. */
  needsAccount: boolean
  href: string
}

const CHOICES: Choice[] = [
  {
    audience: 'owner',
    icon: Store,
    titleKey: 'onboarding.ownerTitle',
    descriptionKey: 'onboarding.ownerDescription',
    needsAccount: true,
    href: '/dashboard/businesses/new',
  },
  {
    audience: 'talent',
    icon: UserRound,
    titleKey: 'onboarding.talentTitle',
    descriptionKey: 'onboarding.talentDescription',
    needsAccount: true,
    href: '/dashboard/talent',
  },
  {
    audience: 'visitor',
    icon: Search,
    titleKey: 'onboarding.visitorTitle',
    descriptionKey: 'onboarding.visitorDescription',
    needsAccount: false,
    href: '/businesses',
  },
]

const STEP_KEYS: TranslationKey[] = [
  'onboarding.step1',
  'onboarding.step2',
  'onboarding.step3',
]

export function AudienceChooser() {
  const t = useT()
  // Read once on mount: a visitor who answers should see the panel change, not
  // the section vanish mid-tap.
  const [hidden, setHidden] = useState(() => readAnswer() !== null)
  const [expanded, setExpanded] = useState<Choice | null>(null)

  if (hidden) return null

  const dismiss = () => {
    remember('dismissed')
    setHidden(true)
  }

  return (
    <section
      className="border-b border-ink-100 bg-white"
      aria-labelledby="audience-heading"
    >
      <div className="container-page py-10 sm:py-12">
        <h2 id="audience-heading" className="text-center text-2xl sm:text-3xl">
          {t('onboarding.heading')}
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-ink-500">
          {t('onboarding.subtitle')}
        </p>

        {expanded ? (
          <div className="mx-auto mt-8 max-w-xl rounded-2xl border-2 border-clay-200 bg-sand-50 p-6">
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
                <Link to="/login" onClick={() => remember(expanded.audience)}>
                  <Check className="h-5 w-5" aria-hidden="true" />
                  {t('onboarding.start')}
                </Link>
              </Button>
              <Button type="button" variant="ghost" size="lg" onClick={() => setExpanded(null)}>
                {t('onboarding.back')}
              </Button>
            </div>
          </div>
        ) : (
          <ul className="mt-8 grid gap-4 sm:grid-cols-3">
            {CHOICES.map((choice) => {
              const Icon = choice.icon
              // Side by side on a phone, stacked from `sm` up. Three tall
              // stacked cards filled an entire mobile screen, which turns a
              // question into the wall this is not supposed to be; laid out in
              // a row, all three and the heading fit in one view.
              const body = (
                <>
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-sand-100 text-clay-600 transition-colors group-hover:bg-clay-500 group-hover:text-white sm:h-14 sm:w-14">
                    <Icon className="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-bold text-ink-900 sm:mt-4 sm:text-lg">
                      {t(choice.titleKey)}
                    </span>
                    <span className="mt-1 block text-sm leading-relaxed text-ink-500">
                      {t(choice.descriptionKey)}
                    </span>
                    <span className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-clay-600 sm:mt-4">
                      {t('onboarding.choose')}
                      <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
                    </span>
                  </span>
                </>
              )

              // A whole-card target, sized for a thumb rather than a cursor.
              const shell =
                'group flex h-full w-full flex-row items-center gap-4 rounded-2xl border-2 border-ink-100 bg-white p-5 text-start transition-colors hover:border-clay-300 hover:bg-sand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2 sm:flex-col sm:items-start sm:gap-0 sm:p-6'

              return (
                <li key={choice.audience}>
                  {choice.needsAccount ? (
                    <button
                      type="button"
                      className={shell}
                      onClick={() => setExpanded(choice)}
                      aria-expanded={false}
                    >
                      {body}
                    </button>
                  ) : (
                    <Link
                      to={choice.href}
                      className={shell}
                      onClick={() => remember(choice.audience)}
                    >
                      {body}
                    </Link>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={dismiss}
            className="text-sm font-medium text-ink-500 underline decoration-ink-100 underline-offset-4 hover:text-ink-700"
          >
            {t('onboarding.dismiss')}
          </button>
        </div>
      </div>
    </section>
  )
}
