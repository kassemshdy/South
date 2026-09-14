import { ShieldCheck } from 'lucide-react'

import { useAuth } from '@/features/auth/AuthContext'
import { WelcomeVideoPlayer } from '@/features/home/WelcomeVideo'
import { AudienceChooser } from '@/features/onboarding/AudienceChooser'
import { useT } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'

export function HomePage() {
  const { isAuthenticated } = useAuth()
  const t = useT()

  useSeo({
    title: t('home.seoTitle'),
    description: t('home.seoDescription'),
    canonicalPath: '/',
  })

  return (
    <>
      {/* The hero is a split, not a cover: the words on the reading-start
          side, Dr Hossam on the other. DOM order does the mirroring — the copy
          comes first, so it lands on the right in Arabic and on the left in
          English without one directional class between them.

          It replaces a wordless cover illustration. That image was 2000px of
          decoration above the fold, and a visitor's first screen said nothing
          about what the site is or what they can do here. */}
      <section className="border-b border-ink-100 bg-gradient-to-b from-sand-100 to-sand-50">
        {/* One grid, three children, and `order` doing the work: on a phone
            the copy comes first, then the video, then the two choices. From
            `lg` up the copy and the player share the first row and the cards
            take the whole width of the second, which is the only way they
            are big — so the two layouts now agree, where they used to
            disagree about which of the video and the cards came first.

            The cards were second here on the argument that they are what
            someone came to make and a 16:9 player above them pushes them
            below the fold. That is still true and is the cost of this
            order: the video is the pitch, and it only works if it is the
            thing you meet before being asked to choose. */}
        <div className="container-page grid items-center gap-10 py-10 sm:py-14 lg:grid-cols-2 lg:gap-x-14 lg:py-20">
          <div className="order-1">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-brand-800 shadow-card">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              {t('home.reviewBadge')}
            </p>

            <h1 className="text-3xl leading-tight sm:text-4xl lg:text-5xl">
              {t('home.heroTitle')}
            </h1>
            <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-500">
              {t('home.heroSubtitle')}
            </p>
          </div>

          <div className="order-2">
            <WelcomeVideoPlayer />
            <p className="mt-3 text-center text-sm font-semibold text-ink-500">
              {t('home.videoHeading')}
            </p>
          </div>

          {/* The one question, in the visitor's own words rather than ours --
              offering something, or looking for something. Which of the two
              someone is decides the whole rest of their visit, so the page
              asks it here and, now, only here.

              This used to be a pair of cards written inline, with the chooser
              repeating the question further down and a third section
              repeating the looking half again. See AudienceChooser for what
              that cost. */}
          <div className="order-3 w-full lg:col-span-2">
            <AudienceChooser isAuthenticated={isAuthenticated} />
          </div>
        </div>
      </section>

      {/* Straight under the hero, against it, and the last thing on the page.
          The four words carry the weight of the whole project, so the mark's
          deep green closes the homepage rather than turning up somewhere in
          the middle of it.

          Six sections used to follow this band: a stats strip, a categories
          grid, the latest listings, a second copy of the browse doors, the
          popular districts, and a closing "add your business" card. Every one
          of them was a directory index rendered on a page nobody comes to for
          an index — and each repeated something the visitor has already been
          offered. The doors are in the chooser above and in the switcher on
          every directory page; the categories and districts are filters on
          `/businesses`, one tap from the header; the listings are the whole of
          `/businesses` itself; and the last card asked for the same thing as
          the chooser's offer half and the footer's link.

          So the homepage now makes one pitch and asks one question, and every
          answer to that question is a real page rather than a preview of one.
          Resist adding a seventh: a strip of latest listings here costs a
          request on every first visit and says less than the band does. */}
      <section
        className="border-y-4 border-wheat-500 bg-brand-700 py-10 sm:py-14"
        aria-label={t('home.sloganTitle')}
      >
        <div className="container-page text-center">
          <p className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-5xl">
            {t('home.sloganTitle')}
          </p>
          <span
            className="mx-auto mt-5 block h-px w-24 bg-wheat-500/70"
            aria-hidden="true"
          />
          <div className="mt-5 flex flex-col items-center justify-center gap-2 text-lg font-semibold text-brand-100 sm:flex-row sm:gap-5 sm:text-xl lg:text-2xl">
            <span>{t('home.sloganLine1')}</span>
            <span className="hidden text-wheat-500 sm:inline" aria-hidden="true">
              •
            </span>
            <span>{t('home.sloganLine2')}</span>
            <span className="hidden text-wheat-500 sm:inline" aria-hidden="true">
              •
            </span>
            <span>{t('home.sloganLine3')}</span>
          </div>

          {/* Last, and in gold, because it is the line that asks something of
              the reader rather than describing us. Kept smaller than the mark
              above it so the band still reads name first, claim second. */}
          <p className="mx-auto mt-7 max-w-3xl font-display text-xl font-bold leading-snug text-wheat-500 sm:text-2xl lg:text-3xl">
            {t('home.sloganCall')}
          </p>
        </div>
      </section>
    </>
  )
}
