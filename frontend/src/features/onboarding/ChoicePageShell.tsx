import { ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useT } from '@/i18n'

/**
 * The chrome shared by `/offer` and `/browse`.
 *
 * These two are real pages, not panels. The homepage used to answer its own
 * question in place: pressing a card swapped the two boxes for two other
 * boxes while the hero, the video and everything below stayed exactly where
 * they were, so the most consequential choice on the site looked like a
 * toggle. It also had no URL, which meant the browser's back button left the
 * homepage instead of stepping back, nothing here could be linked to or sent
 * to somebody over WhatsApp, and no search engine ever saw a word of it.
 *
 * So each half of the question is a page now, and this is the frame: a real
 * heading at page scale, room to breathe, and one way back. The band at the
 * top is what makes it read as somewhere you arrived rather than something
 * that expanded — it is the same deep green the homepage closes on, so the
 * two pages are recognisably part of the same site.
 */
export function ChoicePageShell({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  const t = useT()

  return (
    <div className="bg-sand-50">
      <div className="border-b-4 border-wheat-500 bg-brand-700 py-10 sm:py-14">
        <div className="container-page">
          {/* Back to the homepage, above the title rather than at the foot of
              the page: someone who pressed the wrong card should find the way
              out before they read anything, not after scrolling past it. */}
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-semibold text-wheat-200 hover:text-white"
          >
            <ArrowRight className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
            {t('choice.backHome')}
          </Link>
          <h1 className="mt-4 text-balance text-2xl font-bold text-white sm:text-3xl">
            {title}
          </h1>
          <p className="mt-3 max-w-2xl text-balance leading-relaxed text-wheat-100 sm:text-lg">
            {subtitle}
          </p>
        </div>
      </div>

      <div className="container-page py-10 sm:py-14">{children}</div>
    </div>
  )
}
