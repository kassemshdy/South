import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  MapPin,
  Package,
  Plus,
  ShieldCheck,
  ShoppingBag,
  Store,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { BusinessCardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useAuth } from '@/features/auth/AuthContext'
import { BusinessCard } from '@/features/businesses/BusinessCard'
import { WelcomeVideoPlayer } from '@/features/home/WelcomeVideo'
import { AudienceChooser } from '@/features/onboarding/AudienceChooser'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { publicBusinessApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

export function HomePage() {
  const { isAuthenticated } = useAuth()
  const t = useT()

  useSeo({
    title: t('home.seoTitle'),
    description: t('home.seoDescription'),
    canonicalPath: '/',
  })

  const categories = useCategories()
  const { groups } = useLocationGroups()
  const latest = useQuery({
    queryKey: queryKeys.latestBusinesses(8),
    queryFn: () => publicBusinessApi.latest(8),
  })
  const stats = useQuery({ queryKey: queryKeys.publicStats, queryFn: publicBusinessApi.stats })

  const popularDistricts = groups
    .slice()
    .sort((a, b) => b.district.business_count - a.district.business_count)
    .slice(0, 6)

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
            the copy comes first, then the two choices, and the video last —
            the choices are what someone is here to make, and a 16:9 player
            above them would push both below the fold. From `lg` up the copy
            and the player share the first row and the cards take the whole
            width of the second, which is the only way they are big. */}
        <div className="container-page grid items-center gap-10 py-10 sm:py-14 lg:grid-cols-2 lg:gap-x-14 lg:py-20">
          <div className="order-1">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-clay-700 shadow-card">
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

          <div className="order-3 lg:order-2">
            <WelcomeVideoPlayer />
            <p className="mt-3 text-center text-sm font-semibold text-ink-500">
              {t('home.videoHeading')}
            </p>
          </div>

          {/* The two reasons anybody is on this page, in the visitor's own
              words rather than ours — offering something, or looking for
              something. Which of the two someone is decides the whole rest of
              their visit, so the page asks it first and asks it once.

              Cards rather than buttons, and identical weight: these are two
              halves of one question, not a call to action and its
              afterthought. Each is one whole-card target, and it carries the
              choice and nothing else — a line of explanation under each was
              answering a question nobody had yet asked.

              Centred as a pair across the row rather than tucked under one
              column: with only a line of type in each, two cards hugging the
              heading looked like an accident, and the row they sit under is
              the full width of the hero. */}
          <ul className="order-2 mx-auto grid w-full max-w-2xl gap-4 sm:grid-cols-2 lg:order-3 lg:col-span-2">
            {[
              {
                key: 'offer' as const,
                icon: Store,
                href: isAuthenticated ? '/dashboard/businesses/new' : '/login',
                titleKey: 'home.actionOffer' as const,
              },
              {
                key: 'browse' as const,
                icon: ShoppingBag,
                href: '/products',
                titleKey: 'home.actionBrowse' as const,
              },
            ].map((action) => {
              const Icon = action.icon
              return (
                <li key={action.key}>
                  <Link
                    to={action.href}
                    className="group flex h-full flex-col items-center gap-3 rounded-2xl border-2 border-ink-100 bg-white p-6 text-center shadow-card transition-all hover:-translate-y-0.5 hover:border-clay-300 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2"
                  >
                    <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-sand-100 text-clay-600 transition-colors group-hover:bg-clay-500 group-hover:text-white">
                      <Icon className="h-6 w-6" aria-hidden="true" />
                    </span>
                    <span className="text-lg font-bold leading-snug text-ink-900">
                      {t(action.titleKey)}
                    </span>
                    <span className="flex items-center gap-1.5 text-sm font-semibold text-clay-600">
                      {t('onboarding.choose')}
                      <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      </section>

      {/* Straight under the hero, against it. The four words carry the weight
          of the whole project, so the mark's deep green closes the first
          screen rather than turning up somewhere down the page. */}
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

      {/* These three cards are the homepage's navigation for anyone not
          confident online, and navigation you see once is not navigation.
          They overlap the hero's two cards on purpose: the hero asks the
          question in two halves, these name the third audience — someone
          offering a skill rather than a shop — and spell out what signing up
          involves before anyone is asked for a phone number. */}
      <AudienceChooser isAuthenticated={isAuthenticated} />

      {/* The video used to have a section of its own here. It is in the hero
          now, and one recording twice on one page is one too many. */}

      <section className="container-page py-14" aria-labelledby="discover-heading">
        <h2 id="discover-heading" className="mb-6 text-center text-2xl">
          {t('home.discoverHeading')}
        </h2>
        <div className="grid gap-5 sm:grid-cols-3">
          <DiscoverCard
            icon={Store}
            title={t('home.discoverBusinessesTitle')}
            description={t('home.discoverBusinessesDescription')}
            href="/businesses"
          />
          <DiscoverCard
            icon={Package}
            title={t('home.discoverProductsTitle')}
            description={t('home.discoverProductsDescription')}
            href="/products"
          />
          <DiscoverCard
            icon={Users}
            title={t('home.discoverTalentTitle')}
            description={t('home.discoverTalentDescription')}
            href="/talent"
          />
        </div>
      </section>

      <section className="container-page pb-14" aria-label={t('home.statsHeading')}>
        <div className="mx-auto grid max-w-2xl grid-cols-3 gap-4">
          {stats.isLoading ? (
            <>
              <Skeleton className="h-28 rounded-2xl" />
              <Skeleton className="h-28 rounded-2xl" />
              <Skeleton className="h-28 rounded-2xl" />
            </>
          ) : stats.data ? (
            <>
              <StatTile value={stats.data.total_businesses} label={t('home.statsBusinesses')} />
              <StatTile value={stats.data.total_talents} label={t('home.statsTalents')} />
              <StatTile value={stats.data.total_towns} label={t('home.statsTowns')} />
            </>
          ) : null}
          {/* A failed fetch renders nothing here: this is a decorative strip, not
              a page the visitor came to use, so it must never block or clutter
              the homepage with an error state. */}
        </div>
      </section>

      <section className="container-page py-14" aria-labelledby="categories-heading">
        <h2 id="categories-heading" className="mb-6 text-2xl">
          {t('home.categoriesHeading')}
        </h2>

        {categories.isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {Array.from({ length: 10 }).map((_, index) => (
              <div key={index} className="skeleton h-24 rounded-2xl" />
            ))}
          </div>
        ) : categories.isError ? (
          <ErrorState error={categories.error} onRetry={() => void categories.refetch()} />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {categories.data?.map((category) => (
              <Link
                key={category.id}
                to={`/businesses?category=${encodeURIComponent(category.slug)}`}
                className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-ink-100 bg-white p-5 text-center shadow-card transition-all hover:-translate-y-0.5 hover:border-clay-300 hover:shadow-lift"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sand-100 text-clay-600">
                  <Store className="h-5 w-5" aria-hidden="true" />
                </span>
                <span className="font-semibold text-ink-900">{category.name_ar}</span>
                <span className="text-xs text-ink-500">
                  {t('home.categoryCount', { count: category.business_count })}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="container-page pb-14" aria-labelledby="latest-heading">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h2 id="latest-heading" className="text-2xl">
            {t('home.latestHeading')}
          </h2>
          <Link to="/businesses" className="flex items-center gap-1 font-semibold text-clay-600 hover:text-clay-700">
            {t('home.viewAll')}
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        {latest.isLoading ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <BusinessCardSkeleton key={index} />
            ))}
          </div>
        ) : latest.isError ? (
          <ErrorState error={latest.error} onRetry={() => void latest.refetch()} />
        ) : latest.data && latest.data.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {latest.data.map((business) => (
              <BusinessCard key={business.id} business={business} />
            ))}
          </div>
        ) : (
          <EmptyState
            title={t('home.emptyTitle')}
            description={t('home.emptyDescription')}
            action={
              <Button asChild>
                <Link to={isAuthenticated ? '/dashboard/businesses/new' : '/login'}>
                  {t('nav.addBusiness')}
                </Link>
              </Button>
            }
          />
        )}
      </section>

      {popularDistricts.length > 0 ? (
        <section className="container-page pb-16" aria-labelledby="locations-heading">
          <h2 id="locations-heading" className="mb-6 text-2xl">
            {t('home.locationsHeading')}
          </h2>
          <div className="flex flex-wrap gap-3">
            {popularDistricts.map(({ district }) => (
              <Link
                key={district.id}
                to={`/businesses?location=${encodeURIComponent(district.slug)}`}
                className="inline-flex items-center gap-2 rounded-full border border-ink-100 bg-white px-5 py-2.5 font-semibold shadow-card transition-colors hover:border-clay-300 hover:text-clay-600"
              >
                <MapPin className="h-4 w-4 text-clay-500" aria-hidden="true" />
                {district.name_ar}
                <span className="text-xs font-normal text-ink-500">({district.business_count})</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <section className="border-t border-ink-100 bg-white py-14">
        <div className="container-page text-center">
          <h2 className="text-2xl">{t('home.ctaTitle')}</h2>
          <p className="mx-auto mt-3 max-w-xl text-ink-500">{t('home.ctaBody')}</p>
          <Button asChild size="lg" className="mt-6">
            <Link to={isAuthenticated ? '/dashboard/businesses/new' : '/login'}>
              <Plus className="h-5 w-5" aria-hidden="true" />
              {t('nav.addBusiness')}
            </Link>
          </Button>
        </div>
      </section>
    </>
  )
}

function DiscoverCard({
  icon: Icon,
  title,
  description,
  href,
}: {
  icon: LucideIcon
  title: string
  description: string
  href?: string
}) {
  const t = useT()
  const content: ReactNode = (
    <CardBody className="flex h-full flex-col items-center gap-2 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-sand-100 text-clay-600">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <span className="flex items-center gap-2 font-bold text-ink-900">
        {title}
        {!href ? <Badge className="bg-sand-100 text-clay-700">{t('home.comingSoon')}</Badge> : null}
      </span>
      <span className="text-sm text-ink-500">{description}</span>
    </CardBody>
  )

  if (!href) {
    return (
      <Card aria-disabled="true" className="opacity-60">
        {content}
      </Card>
    )
  }

  return (
    <Card className="transition-all hover:-translate-y-0.5 hover:border-clay-300 hover:shadow-lift">
      <Link to={href} className="block h-full">
        {content}
      </Link>
    </Card>
  )
}

function StatTile({ value, label }: { value: number; label: string }) {
  return (
    <Card>
      <CardBody className="text-center">
        <p className="ltr-nums text-3xl font-bold text-clay-900">{value}</p>
        <p className="mt-1 text-sm text-ink-500">{label}</p>
      </CardBody>
    </Card>
  )
}
