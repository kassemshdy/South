import { AlertTriangle, Check, UserCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { ChoicePageShell } from '@/features/onboarding/ChoicePageShell'
import { DoorBody, doorCard } from '@/features/onboarding/DoorCard'
import { OfferVideo } from '@/features/onboarding/OfferVideo'
import { destinationFor, OFFER_DOORS, type Door } from '@/features/onboarding/destinations'
import { useScrollToStep } from '@/hooks/useScrollToStep'
import { usePageText } from '@/hooks/usePageText'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'

const STEP_KEYS: TranslationKey[] = [
  'onboarding.step1',
  'onboarding.step2',
  'onboarding.step3',
]

const ELIGIBILITY_KEYS: TranslationKey[] = [
  'offerPage.eligibilityOne',
  'offerPage.eligibilityTwo',
]

/**
 * Listing something: its own page, at `/offer`.
 *
 * Round 3: for a visitor without an account, choosing a door now goes
 * straight to the application, which holds the notice, the steps and the
 * form on one page -- it used to be three (the notice, a steps panel ending
 * in a start button, then the form).
 *
 * This used to happen inside the homepage. Pressing "I want to list" swapped
 * two cards for two other cards while the hero, the video and everything
 * below stayed put, so the most consequential choice on the site read as a
 * toggle — and it had no URL, so the back button left the homepage, nothing
 * could be linked, and search engines saw none of it.
 *
 * **Who may list is on the page, before the doors.** The platform is open to
 * southerners in its first phase and to further groups after that, and
 * somebody who does not qualify should find that out here rather than after
 * filling in a form and waiting for a rejection. It sits above the steps for
 * the same reason the steps sit above the form: the order is the honest one.
 *
 * The responsibility notice still stands between a door and the page behind
 * it, and still asks every time. What changed is where it stands, not
 * whether.
 */
export function OfferPage() {
  const t = useT()
  const { isAuthenticated } = useAuth()
  useSeo({ title: `${t('offerPage.title')} | ${t('app.name')}`, description: t('offerPage.subtitle') })
  // Editable from the admin's pages screen: one item per line of the body,
  // and the built-in list wherever nothing has been written.
  const eligibility = usePageText('offer_eligibility')
  const eligibilityItems = eligibility.body
    ? eligibility.body.split('\n').map((line) => line.trim()).filter(Boolean)
    : ELIGIBILITY_KEYS.map((key) => t(key))

  const [pending, setPending] = useState<Door | null>(null)

  // The doors sit a long way down this page and the notice that replaces
  // them is short, so without this a visitor presses a card and sees nothing
  // move.
  useScrollToStep(pending ? `pending:${pending.key}` : 'doors')

  if (pending) {
    return (
      <ChoicePageShell page="offer" title={t('consent.heading')} subtitle={t(pending.titleKey)}>
        <div className="mx-auto max-w-2xl rounded-2xl border-2 border-clay-300 bg-white p-6 sm:p-8">
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-800"
            aria-hidden="true"
          >
            <AlertTriangle className="h-6 w-6" />
          </span>
          <p className="mt-5 leading-relaxed text-ink-700 sm:text-lg">{t('consent.body')}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link to={destinationFor(pending, isAuthenticated)}>
                <Check className="h-5 w-5" aria-hidden="true" />
                {t('consent.agree')}
              </Link>
            </Button>
            <Button type="button" variant="ghost" size="lg" onClick={() => setPending(null)}>
              {t('onboarding.back')}
            </Button>
          </div>
        </div>
      </ChoicePageShell>
    )
  }

  return (
    <ChoicePageShell page="offer" title={t('offerPage.title')} subtitle={t('offerPage.subtitle')}>
      <div className="mx-auto max-w-3xl space-y-10">
        {/* Before anything else on the page: whether this is for you. */}
        <section className="rounded-2xl border-2 border-olive-200 bg-white p-6 sm:p-8">
          <h2 className="flex items-center gap-3 text-lg font-bold text-ink-900">
            <span
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-olive-100 text-olive-700"
              aria-hidden="true"
            >
              <UserCheck className="h-5 w-5" />
            </span>
            {eligibility.title ?? t('offerPage.eligibilityTitle')}
          </h2>
          <ol className="mt-5 space-y-3">
            {eligibilityItems.map((item, index) => (
              <li key={index} className="flex items-start gap-3">
                <span
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sand-100 text-sm font-bold text-brand-800 ltr-nums"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="leading-relaxed text-ink-700">{item}</span>
              </li>
            ))}
          </ol>
          <p className="mt-5 border-t border-ink-100 pt-4 text-sm leading-relaxed text-ink-500">
            {eligibility.summary ?? t('offerPage.eligibilityNote')}
          </p>
        </section>

        {/* Before the steps, as the owners asked: nothing until an
            administrator sets the video. */}
        <OfferVideo />

        <section>
          <h2 className="text-lg font-bold text-ink-900">{t('offerPage.stepsTitle')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('onboarding.stepsIntro')}</p>
          <ol className="mt-5 grid gap-4 sm:grid-cols-3">
            {STEP_KEYS.map((key, index) => (
              <li key={key} className="rounded-2xl border border-ink-100 bg-white p-5">
                <span
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-700 text-sm font-bold text-white ltr-nums"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="mt-3 block text-sm leading-relaxed text-ink-700">{t(key)}</span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <h2 className="text-lg font-bold text-ink-900">{t('offerPage.doorsTitle')}</h2>
          {/* Without an account, a door is a link straight to the one-page
              application, which carries the responsibility notice and the
              steps itself (round 3: one page instead of three). Signed in, it
              is a button: the notice still stands before the dashboard. */}
          <ul className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {OFFER_DOORS.map((door) => (
              <li key={door.key}>
                {isAuthenticated ? (
                  <button type="button" className={doorCard('offer')} onClick={() => setPending(door)}>
                    <DoorBody door={door} />
                  </button>
                ) : (
                  <Link to={destinationFor(door, false)} className={doorCard('offer')}>
                    <DoorBody door={door} />
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </ChoicePageShell>
  )
}
