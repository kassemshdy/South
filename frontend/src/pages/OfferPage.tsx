import { AlertTriangle, Check, UserCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
import { ChoicePageShell } from '@/features/onboarding/ChoicePageShell'
import { DOOR_CARD, DoorBody } from '@/features/onboarding/DoorCard'
import { destinationFor, OFFER_DOORS, type Door } from '@/features/onboarding/destinations'
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

  const [pending, setPending] = useState<Door | null>(null)
  const [agreed, setAgreed] = useState<Door | null>(null)

  // Someone already signed in has been through the three steps and has an
  // account, so agreeing is the last thing between them and the wizard.
  const stepsNeeded = !isAuthenticated

  if (agreed) {
    return (
      <ChoicePageShell title={t(agreed.titleKey)} subtitle={t('onboarding.stepsIntro')}>
        <div className="mx-auto max-w-2xl">
          <ol className="space-y-5">
            {STEP_KEYS.map((key, index) => (
              <li key={key} className="flex items-start gap-4">
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-700 font-bold text-white ltr-nums"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="pt-1 leading-relaxed text-ink-700">{t(key)}</span>
              </li>
            ))}
          </ol>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              {/* Straight to the application form, never to /login: there is
                  no account to sign into yet, and the form is step one of the
                  three just described. */}
              <Link to={destinationFor(agreed, isAuthenticated)}>
                <Check className="h-5 w-5" aria-hidden="true" />
                {t('onboarding.start')}
              </Link>
            </Button>
            <Button type="button" variant="ghost" size="lg" onClick={() => setAgreed(null)}>
              {t('onboarding.back')}
            </Button>
          </div>

          <AssistedListing contextKey="assisted.contextHome" />
        </div>
      </ChoicePageShell>
    )
  }

  if (pending) {
    return (
      <ChoicePageShell title={t('consent.heading')} subtitle={t(pending.titleKey)}>
        <div className="mx-auto max-w-2xl rounded-2xl border-2 border-clay-300 bg-white p-6 sm:p-8">
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-800"
            aria-hidden="true"
          >
            <AlertTriangle className="h-6 w-6" />
          </span>
          <p className="mt-5 leading-relaxed text-ink-700 sm:text-lg">{t('consent.body')}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            {stepsNeeded ? (
              <Button
                type="button"
                size="lg"
                onClick={() => {
                  setAgreed(pending)
                  setPending(null)
                }}
              >
                <Check className="h-5 w-5" aria-hidden="true" />
                {t('consent.agree')}
              </Button>
            ) : (
              <Button asChild size="lg">
                <Link to={destinationFor(pending, isAuthenticated)}>
                  <Check className="h-5 w-5" aria-hidden="true" />
                  {t('consent.agree')}
                </Link>
              </Button>
            )}
            <Button type="button" variant="ghost" size="lg" onClick={() => setPending(null)}>
              {t('onboarding.back')}
            </Button>
          </div>
        </div>
      </ChoicePageShell>
    )
  }

  return (
    <ChoicePageShell title={t('offerPage.title')} subtitle={t('offerPage.subtitle')}>
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
            {t('offerPage.eligibilityTitle')}
          </h2>
          <ol className="mt-5 space-y-3">
            {ELIGIBILITY_KEYS.map((key, index) => (
              <li key={key} className="flex items-start gap-3">
                <span
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sand-100 text-sm font-bold text-brand-800 ltr-nums"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="leading-relaxed text-ink-700">{t(key)}</span>
              </li>
            ))}
          </ol>
          <p className="mt-5 border-t border-ink-100 pt-4 text-sm leading-relaxed text-ink-500">
            {t('offerPage.eligibilityNote')}
          </p>
        </section>

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
          {/* Buttons rather than links: the responsibility notice is the only
              way through an offering door, and a link would skip it. */}
          <ul className="mt-5 grid gap-4 sm:grid-cols-2">
            {OFFER_DOORS.map((door) => (
              <li key={door.key}>
                <button type="button" className={DOOR_CARD} onClick={() => setPending(door)}>
                  <DoorBody door={door} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </ChoicePageShell>
  )
}
