import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  MapPin,
  Package,
  Plus,
  Search,
  ShieldCheck,
  Store,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { BusinessCardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { BusinessCard } from '@/features/businesses/BusinessCard'
import { useAuth } from '@/features/auth/AuthContext'
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import { useSeo } from '@/hooks/useSeo'
import { publicBusinessApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

export function HomePage() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
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

  const handleSearch = (event: FormEvent) => {
    event.preventDefault()
    navigate(query.trim() ? `/businesses?q=${encodeURIComponent(query.trim())}` : '/businesses')
  }

  const popularDistricts = groups
    .slice()
    .sort((a, b) => b.district.business_count - a.district.business_count)
    .slice(0, 6)

  return (
    <>
      <section className="relative overflow-hidden border-b border-ink-100 bg-gradient-to-b from-sand-100 to-sand-50">
        <div className="container-page py-14 text-center sm:py-20">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-clay-700 shadow-card">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            {t('home.reviewBadge')}
          </p>

          <h1 className="mx-auto max-w-3xl text-3xl leading-tight sm:text-4xl lg:text-5xl">
            {t('home.heroTitle')}
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg leading-relaxed text-ink-500">
            {t('home.heroSubtitle')}
          </p>

          <form onSubmit={handleSearch} className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row" role="search">
            <label htmlFor="home-search" className="sr-only">
              {t('home.searchLabel')}
            </label>
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute inset-y-0 start-4 my-auto h-5 w-5 text-ink-300"
                aria-hidden="true"
              />
              <input
                id="home-search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t('home.searchPlaceholder')}
                className="h-14 w-full rounded-2xl border-2 border-ink-100 bg-white ps-12 pe-4 text-[15px] shadow-card placeholder:text-ink-300 focus:border-clay-400 focus:outline-none focus:ring-2 focus:ring-clay-500/20"
              />
            </div>
            <Button type="submit" size="lg" className="sm:w-auto">
              {t('common.search')}
            </Button>
          </form>

          <div className="mt-6">
            <Button asChild variant="outline" size="lg">
              <Link to={isAuthenticated ? '/dashboard/businesses/new' : '/login'}>
                <Plus className="h-5 w-5" aria-hidden="true" />
                {t('home.addBusiness')}
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="overflow-hidden bg-sand-100" aria-hidden="true">
        <img src="/home-cover.png" alt="" className="h-auto w-full" loading="eager" />
      </section>

      <section className="border-y border-olive-200 bg-olive-50 py-5" aria-label={t('home.sloganTitle')}>
        <div className="container-page flex flex-col items-center justify-center gap-2 text-center sm:flex-row sm:gap-4">
          <span className="text-sm font-bold text-olive-700">{t('home.sloganTitle')}</span>
          <span className="hidden text-olive-300 sm:inline">•</span>
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm font-semibold text-olive-800">
            <span>{t('home.sloganLine1')}</span>
            <span className="text-olive-300">•</span>
            <span>{t('home.sloganLine2')}</span>
            <span className="text-olive-300">•</span>
            <span>{t('home.sloganLine3')}</span>
          </div>
        </div>
      </section>

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
