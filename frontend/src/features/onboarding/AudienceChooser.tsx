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
 *
 * **Two colours, chosen by the CEO**, who asked for these to look grander as
 * the site's main entrance: olive green for offering, terracotta for looking.
 * Equal weight, told apart at a glance before a word is read. White on the
 * darker end of each gradient, where the title sits, clears AA for large
 * bold text in both.
 */

interface Half {
  to: string
  icon: typeof Store
  titleKey: TranslationKey
  /** The card's gradient, and the icon's colour on its white disc. */
  surface: string
  iconColor: string
}

const HALVES: Half[] = [
  {
    to: '/offer',
    icon: Store,
    titleKey: 'home.actionOffer',
    surface: 'from-brand-600 to-brand-800',
    iconColor: 'text-brand-700',
  },
  {
    to: '/browse',
    icon: ShoppingBag,
    titleKey: 'home.actionBrowse',
    surface: 'from-clay-500 to-clay-700',
    iconColor: 'text-clay-600',
  },
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
                className={`group relative isolate flex h-full min-h-[18rem] w-full flex-col items-center justify-center gap-5 overflow-hidden rounded-3xl bg-gradient-to-br ${half.surface} p-8 text-center shadow-lift transition-all duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-wheat-500 focus-visible:ring-offset-2 sm:p-10`}
              >
                {/* Two soft discs of light, for depth without a picture to
                    license: the card reads as a surface, not a flat fill. */}
                <span aria-hidden="true" className="absolute -end-10 -top-10 -z-10 h-44 w-44 rounded-full bg-white/10" />
                <span aria-hidden="true" className="absolute -bottom-14 -start-8 -z-10 h-40 w-40 rounded-full bg-white/5" />
                <span className="flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-lg transition-transform duration-300 group-hover:scale-105 sm:h-24 sm:w-24">
                  <Icon className={`h-9 w-9 sm:h-11 sm:w-11 ${half.iconColor}`} aria-hidden="true" />
                </span>
                <span className="text-balance text-xl font-bold leading-snug text-white sm:text-2xl">
                  {t(half.titleKey)}
                </span>
                {/* A filled pill rather than a line of coloured text: at this
                    size the words under the title were reading as a caption,
                    and this is the thing to press. */}
                <span className="mt-2 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 font-bold text-ink-900 transition-transform group-hover:scale-105">
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
