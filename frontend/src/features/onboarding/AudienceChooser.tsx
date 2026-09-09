import { ArrowLeft, Check, Search, Store, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
import { useT, type TranslationKey } from '@/i18n'

/**
 * The three ways into the site, always on the homepage.
 *
 * It started as a first-visit question that remembered its answer and then got
 * out of the way. That was the wrong instinct for this site: these three cards
 * *are* the homepage's navigation for people who are not confident online, and
 * something you only see once cannot be navigation. So it is permanent, and it
 * carries no dismissal and no memory.
 *
 * Written for someone who is not confident online: three large targets, one
 * short line each, no jargon. It is still never a wall — everything below it
 * stays reachable, and nothing here has to be answered to use the site.
 *
 * For a visitor who is not signed in, choosing to list something does not jump
 * straight to a phone-number prompt: it opens the three steps involved first,
 * in place, because "sign in" as an answer to "I have a shop" tells you
 * nothing about what you are agreeing to. Someone already signed in has been
 * through that, so their cards go straight to the real destination.
 */

type Audience = 'owner' | 'talent' | 'visitor'

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

export function AudienceChooser({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const t = useT()
  const [expanded, setExpanded] = useState<Choice | null>(null)

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
                <Link to="/login">
                  <Check className="h-5 w-5" aria-hidden="true" />
                  {t('onboarding.start')}
                </Link>
              </Button>
              <Button type="button" variant="ghost" size="lg" onClick={() => setExpanded(null)}>
                {t('onboarding.back')}
              </Button>
            </div>

            {/* Offered here, next to the three steps, rather than after a
                failed attempt: someone who reads "register with your phone
                number" and decides it is not for them never reaches a later
                screen to be rescued on. Absent for the visitor card, which
                needs no account and no help. */}
            {expanded.needsAccount ? (
              <AssistedListing contextKey="assisted.contextHome" />
            ) : null}
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
                  {/* Only an anonymous visitor needs the explanation first;
                      for someone signed in these are plain shortcuts to the
                      part of their dashboard the card describes. */}
                  {choice.needsAccount && !isAuthenticated ? (
                    <button
                      type="button"
                      className={shell}
                      onClick={() => setExpanded(choice)}
                      aria-expanded={false}
                    >
                      {body}
                    </button>
                  ) : (
                    <Link to={choice.href} className={shell}>
                      {body}
                    </Link>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}
