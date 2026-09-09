import { MessageCircle } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useT, type TranslationKey } from '@/i18n'
import { whatsappHref } from '@/utils/format'

const SUPPORT_NUMBER = import.meta.env.VITE_SUPPORT_WHATSAPP as string | undefined

/**
 * "Contact us and we will list it for you."
 *
 * Onboarding has been made shorter twice now — five required fields, optional
 * steps collapsed, plain-language steps before any phone prompt. All of that
 * helps someone who is willing to *try*. It does nothing for the person who
 * will not try at all, and in the audience this project exists for that is a
 * lot of people. For them the answer is not a shorter form; it is a human
 * being on WhatsApp.
 *
 * Two things make this honest rather than decorative:
 *
 * - **It is offered before someone gives up, not after.** On the homepage
 *   card and inside the wizard, next to the thing they are stuck on.
 * - **It does not exist until someone can answer it.** The whole block is
 *   absent when `VITE_SUPPORT_WHATSAPP` is unset, the same discipline the
 *   Sentry DSN, the analytics id and the social links follow. A "contact us"
 *   that goes nowhere is worse than none: it spends the one attempt a
 *   hesitant person was willing to make.
 *
 * The guard is `whatsappHref` itself, which returns null for a missing number
 * *and* for one with no digits in it — so a variable set to a placeholder or
 * to an empty string renders nothing rather than a broken link.
 */
export function AssistedListing({ contextKey }: { contextKey: TranslationKey }) {
  const t = useT()

  // Naming where they were when they asked, so whoever answers opens the
  // conversation already knowing what the person was trying to do.
  const href = whatsappHref(
    SUPPORT_NUMBER ?? null,
    t('assisted.message', { context: t(contextKey) }),
  )
  if (!href) return null

  return (
    <div className="mt-6 rounded-xl border border-brand-200 bg-brand-50 p-4">
      <p className="font-semibold text-brand-900">{t('assisted.title')}</p>
      <p className="mt-1 text-sm leading-relaxed text-brand-800">{t('assisted.body')}</p>
      <div className="mt-3">
        <Button asChild variant="secondary">
          <a href={href} target="_blank" rel="noreferrer noopener">
            <MessageCircle className="h-5 w-5" aria-hidden="true" />
            {t('assisted.cta')}
          </a>
        </Button>
      </div>
      {/* What happens next. Deliberately not a response time: an unanswered
          promise is worse than no promise, and nothing here knows how fast
          the team actually replies. That a person reads it is both true and
          the thing a hesitant sender wants to know. */}
      <p className="mt-2.5 text-xs text-brand-700">{t('assisted.human')}</p>
    </div>
  )
}
