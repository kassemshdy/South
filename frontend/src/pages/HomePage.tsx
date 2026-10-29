import { Handshake, ShieldCheck } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import {
  BlogSection,
  CategoriesSection,
  CategoryProductsSection,
  NewsSection,
  ProductsSection,
  TopRatedProductsSection,
  TopViewedProductsSection,
  MostOrderedProductsSection,
  TestimonialsSection,
  WorkshopsSection,
  OnlineWorkshopsSection,
  ReelsSection,
  SearchSection,
  ShopsSection,
  StatsSection,
  StoriesSection,
  TalentsSection,
} from '@/features/home/HomeSections'
import {
  ORIGINAL_ORDER,
  PREVIEW_PARAM,
  PREVIEW_VALUE,
  PROPOSED_ORDER,
} from '@/features/home/layout'
import { WelcomeVideoPlayer } from '@/features/home/WelcomeVideo'
import { AudienceChooser } from '@/features/onboarding/AudienceChooser'
import { useT } from '@/i18n'
import { usePageCover } from '@/hooks/usePageCover'
import { usePageText } from '@/hooks/usePageText'
import { useSeo } from '@/hooks/useSeo'
import { homeApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { HomeSectionId } from '@/types/api'

const SECTIONS: Record<HomeSectionId, () => ReactNode> = {
  cover: () => <CoverSection />,
  hero: () => <HeroSection />,
  slogan: () => <SloganSection />,
  search: () => <SearchSection />,
  categories: () => <CategoriesSection />,
  stories: () => <StoriesSection />,
  reels: () => <ReelsSection />,
  stats: () => <StatsSection />,
  products: () => <ProductsSection />,
  top_rated_products: () => <TopRatedProductsSection />,
  top_viewed_products: () => <TopViewedProductsSection />,
  most_ordered_products: () => <MostOrderedProductsSection />,
  testimonials: () => <TestimonialsSection />,
  workshops: () => <WorkshopsSection />,
  online_workshops: () => <OnlineWorkshopsSection />,
  category_products: () => <CategoryProductsSection />,
  shops: () => <ShopsSection />,
  talents: () => <TalentsSection />,
  news: () => <NewsSection />,
  blog: () => <BlogSection />,
}

export function HomePage() {
  const t = useT()
  const [searchParams] = useSearchParams()
  // The manager's review of the proposed page, on live data, saving
  // nothing: every proposed section in the proposed order.
  const preview = searchParams.get(PREVIEW_PARAM) === PREVIEW_VALUE
  const layout = useQuery({ queryKey: queryKeys.homeLayout, queryFn: homeApi.layout })

  useSeo({
    title: t('home.seoTitle'),
    description: t('home.seoDescription'),
    canonicalPath: '/',
    noIndex: preview,
  })

  const order = preview
    ? PROPOSED_ORDER
    : layout.data
      ? layout.data.sections.filter((section) => section.visible).map((section) => section.id)
      : ORIGINAL_ORDER

  return (
    <>
      {preview ? (
        <div className="bg-wheat-200 py-2 text-center text-sm font-semibold text-ink-900">
          {t('home.previewBanner')}
        </div>
      ) : null}
      {order.map((id) =>
        SECTIONS[id] ? <SectionSlot key={id}>{SECTIONS[id]()}</SectionSlot> : null,
      )}
    </>
  )
}

function SectionSlot({ children }: { children: ReactNode }) {
  return <>{children}</>
}

function CoverSection() {
  const t = useT()
  const southCover = usePageCover('home')
  // An administrator's words where they wrote some (round 3), the shipped
  // catalog text where they did not.
  const text = usePageText('home')
  return (
    <>
    {/* The first thing under the menu: the place itself. It used to close
        the page, under the green band; it moved up so a visitor meets the
        South before anything else. The message sits over the image in a
        scrim so the coastline is the thing you look at, and the words are
        what you read while looking at it.
        `object-cover` with a fixed height rather than the image's own
        aspect: a 16:9 photograph at phone width is a letterbox strip, and
        this needs to feel like somewhere you could stand. */}
    <section className="relative isolate" aria-label={text.title ?? t('home.southTitle')}>
      <img
        src={southCover.src}
        // The alt text describes the default photograph; over one an
        // administrator uploaded it would be wrong, and the heading beside
        // it already names the section.
        alt={southCover.custom ? '' : t('home.southImageAlt')}
        width={1200}
        height={630}
        // Above the fold now, so fetched first rather than lazily.
        fetchPriority="high"
        decoding="async"
        // A little shorter than it was at the foot, so the pitch and the
        // two choices under it are not pushed a whole screen down.
        className="h-[18rem] w-full object-cover sm:h-[22rem] lg:h-[26rem]"
      />
      {/* Heavy at the foot and quick to clear: the text lands over open
          water, the brightest part of the photograph, and a gentler scrim
          left white-on-pale-blue. Written out rather than assembled from
          `from-`/`via-`/`to-` utilities because it needs four stops with
          chosen positions, and the two-stop version was not dark enough
          where the words actually sit. ink-900, the same colour the rest of
          the page sets text in. */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'linear-gradient(to top, rgba(31,30,28,0.94) 0%, rgba(31,30,28,0.82) 22%, rgba(31,30,28,0.35) 55%, rgba(31,30,28,0) 82%)',
        }}
        aria-hidden="true"
      />
      <div className="container-page absolute inset-x-0 bottom-0 pb-8 sm:pb-12">
        <div className="max-w-2xl">
          <h2 className="font-display text-2xl font-bold text-white sm:text-3xl lg:text-4xl">
            {text.title ?? t('home.southTitle')}
          </h2>
          <p className="mt-3 whitespace-pre-line text-base leading-relaxed text-white/90 sm:text-lg">
            {text.summary ?? t('home.southBody')}
          </p>
        </div>
      </div>
    </section>
    </>
  )
}

function HeroSection() {
  const t = useT()
  const text = usePageText('home')
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
          {/* The owners' own sentence, set apart in a contrasting colour
              because they asked for it to read as the most important line
              on the page. */}
          <p className="mt-4 max-w-xl rounded-xl border-s-4 border-clay-500 bg-clay-50 px-4 py-3 text-sm font-semibold leading-relaxed text-clay-800">
            {t('home.disclaimer')}
          </p>
        </div>

        <div className="order-2">
          <WelcomeVideoPlayer />
          <p className="mt-3 text-center text-sm font-semibold text-ink-500">
            {text.body ?? t('home.videoHeading')}
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
          <AudienceChooser />
        </div>

        {/* The owners' third way in (round 3): not selling or buying, but
            supporting. Under the chooser rather than a section of its own,
            for the reason given above the green band below. */}
        <Link
          to="/partner"
          className="order-4 flex w-full items-center gap-4 rounded-2xl border-2 border-olive-200 bg-white p-5 shadow-card transition-colors hover:border-olive-400 lg:col-span-2"
        >
          <span
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-olive-100 text-olive-700"
            aria-hidden="true"
          >
            <Handshake className="h-6 w-6" />
          </span>
          <span className="flex-1">
            <span className="block text-lg font-bold text-ink-900">{t('partner.title')}</span>
            <span className="mt-0.5 block text-sm font-semibold text-brand-700">
              {t('partner.cardCta')}
            </span>
          </span>
        </Link>
      </div>
    </section>
    </>
  )
}

function SloganSection() {
  const t = useT()
  return (
    <>
    {/* Straight under the hero, against it, and now the last thing on the
        page again: the photograph that used to follow it opens the page.
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

        The owners asked for them back as browsing sections (27 Oct 2026):
        search, categories, stories, counts, newest products, shops,
        services and news now live in features/home/HomeSections and are
        ordered, with these three, from /admin/home-layout. A fresh site
        still shows this band right after the hero; where it sits now is the
        administrators' choice. */}
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
