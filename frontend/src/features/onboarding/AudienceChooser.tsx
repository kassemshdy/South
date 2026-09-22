import { ArrowLeft, ShoppingBag, Store } from 'lucide-react'
import { Link } from 'react-router-dom'

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
 * **And it is two links now, not a four-level state machine.** Everything
 * behind the question — which kind, the responsibility notice, the three
 * steps — used to happen right here, in place: pressing a card swapped these
 * two boxes for two other boxes while the hero above and the whole page below
 * stayed exactly where they were. The most consequential choice on the site
 * read as a toggle. It also had no URL, so the browser's back button left the
 * homepage rather than stepping back, none of it could be sent to somebody
 * over WhatsApp, and no search engine ever saw a word of it.
 *
 * So each half is a page: `/offer` and `/browse`. This component is now only
 * the question and the two ways out of it, which is all the homepage should
 * have been asked to carry.
 *
 * Identical weight on the two, because these are two halves of one question
 * rather than a call to action and its afterthought. No line of explanation
 * under either: it was answering a question nobody had yet asked.
 */

interface Half {
  to: string
  icon: typeof Store
  titleKey: TranslationKey
}

const HALVES: Half[] = [
  { to: '/offer', icon: Store, titleKey: 'home.actionOffer' },
  { to: '/browse', icon: ShoppingBag, titleKey: 'home.actionBrowse' },
]

export function AudienceChooser() {
  const t = useT()

  return (
    <div className="mx-auto w-full max-w-4xl">
      {/* The question is asked out loud rather than implied by two cards. It
          carries the section: these two are the homepage's navigation for
          someone who is not confident online, so the label above them is sized
          to be read rather than skimmed past. */}
      <h2 className="text-center text-xl font-bold text-ink-900 sm:text-2xl">
        {t('onboarding.heading')}
      </h2>
      <p className="mx-auto mt-2 max-w-lg text-center text-ink-500 sm:text-lg">
        {t('onboarding.subtitle')}
      </p>

      {/* Wide gaps on purpose: two targets this large read as two choices
          only when there is room between them. Below `sm` they stack, and the
          gap becomes vertical breathing space rather than a gutter. */}
      <ul className="mt-8 grid gap-6 sm:mt-10 sm:grid-cols-2 sm:gap-8">
        {HALVES.map((half) => {
          const Icon = half.icon
          return (
            <li key={half.to}>
              <Link
                to={half.to}
                className="group flex h-full w-full flex-col items-center gap-5 rounded-3xl border-2 border-ink-100 bg-white p-8 text-center shadow-card transition-all duration-200 hover:-translate-y-1 hover:border-brand-400 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 sm:p-10"
              >
                <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-sand-100 text-brand-700 transition-colors group-hover:bg-brand-700 group-hover:text-white sm:h-20 sm:w-20">
                  <Icon className="h-8 w-8 sm:h-9 sm:w-9" aria-hidden="true" />
                </span>
                <span className="text-balance text-xl font-bold leading-snug text-ink-900 sm:text-2xl">
                  {t(half.titleKey)}
                </span>
                {/* A filled pill rather than a line of coloured text: at this
                    size the words under the title were reading as a caption,
                    and this is the thing to press. */}
                <span className="mt-auto inline-flex items-center gap-2 rounded-full bg-sand-100 px-5 py-2.5 font-semibold text-brand-800 transition-colors group-hover:bg-brand-700 group-hover:text-white">
                  {t('onboarding.choose')}
                  <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
