/**
 * The browsing sections of the home page (the owners' request, 27 Oct
 * 2026): search, categories, stories, Instagram reels, live counts, newest
 * products, shops, services and news. Each is one self-contained section an administrator
 * can move or hide at /admin/home-layout; each renders nothing while it has
 * nothing to show, so an empty one never leaves a heading over a blank.
 *
 * They reuse the directories' own cards and queries, so a product looks the
 * same here as on /products and shares its cache.
 */

import { useQuery } from '@tanstack/react-query'
import { Instagram, Play, Search } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { BusinessCard } from '@/features/businesses/BusinessCard'
import { CategoryIcon } from '@/features/home/categoryIcon'
import { ReelPlayer, reelCaption } from '@/features/home/ReelPlayer'
import { ProductCard } from '@/features/items/ProductCard'
import { TalentCard } from '@/features/talent/TalentCard'
import { useI18n, useT } from '@/i18n'
import {
  homeApi,
  publicArticleApi,
  publicBusinessApi,
  publicItemApi,
  publicTalentApi,
  reelApi,
  taxonomyApi,
} from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Category, GoodsOrigin, HomeStory, ProductQuery } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/format'

function SectionHeading({ title, to, more }: { title: string; to?: string; more?: string }) {
  return (
    <div className="mb-5 flex items-baseline justify-between gap-4">
      <h2 className="font-display text-2xl font-bold text-ink-900 sm:text-3xl">{title}</h2>
      {to && more ? (
        <Link to={to} className="shrink-0 text-sm font-semibold text-brand-700 hover:underline">
          {more}
        </Link>
      ) : null}
    </div>
  )
}

function Band({ children, tone = 'plain' }: { children: ReactNode; tone?: 'plain' | 'sand' }) {
  return (
    <section className={cn('py-10 sm:py-12', tone === 'sand' ? 'bg-sand-100' : 'bg-sand-50')}>
      <div className="container-page">{children}</div>
    </section>
  )
}

export function SearchSection() {
  const t = useT()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const term = q.trim()
    navigate(term ? `/products?q=${encodeURIComponent(term)}` : '/products')
  }
  return (
    <section className="bg-brand-700 py-6 sm:py-8">
      <form onSubmit={submit} className="container-page flex gap-2" role="search">
        <label htmlFor="home-search" className="sr-only">
          {t('products.searchLabel')}
        </label>
        <input
          id="home-search"
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder={t('products.searchLabel')}
          className="h-12 min-w-0 flex-1 rounded-xl border-0 bg-white px-4 text-base text-ink-900 shadow-card focus:outline-none focus:ring-2 focus:ring-wheat-500"
        />
        <button
          type="submit"
          className="flex h-12 items-center gap-2 rounded-xl bg-clay-500 px-5 font-semibold text-white hover:bg-clay-600"
        >
          <Search className="h-5 w-5" aria-hidden="true" />
          <span className="hidden sm:inline">{t('common.search')}</span>
        </button>
      </form>
    </section>
  )
}

export function CategoriesSection() {
  const t = useT()
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: taxonomyApi.categories })
  const list = (categories.data ?? []).filter((category) => category.is_active !== false)
  if (list.length === 0) return null
  return (
    <Band>
      <SectionHeading title={t('home.categoriesTitle')} />
      <ul className="flex gap-3 overflow-x-auto pb-2">
        {list.map((category) => (
          <li key={category.id} className="shrink-0">
            <Link
              to={`/products?category=${encodeURIComponent(category.slug)}`}
              className="flex w-28 flex-col items-center gap-2 rounded-2xl border border-ink-100 bg-white p-3 text-center shadow-card transition-colors hover:border-brand-300"
            >
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                <CategoryIcon name={category.icon} className="h-7 w-7" />
              </span>
              <span className="text-sm font-semibold leading-snug text-ink-900">{category.name_ar}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Band>
  )
}

export function StoriesSection() {
  const t = useT()
  const stories = useQuery({ queryKey: queryKeys.homeStories, queryFn: homeApi.stories })
  const [open, setOpen] = useState<HomeStory | null>(null)
  if (!stories.isSuccess) return null
  // No listing has a video yet: the row shows our own Instagram reels
  // instead, rather than disappearing (the owners' request, 28 Oct 2026).
  if (stories.data.length === 0) return <ReelStories />
  const pageOf = (story: HomeStory) =>
    `/${story.kind === 'business' ? 'business' : 'talent'}/${encodeURIComponent(story.slug)}`
  return (
    <section className="border-b border-ink-100 bg-white py-6">
      <div className="container-page">
        <h2 className="mb-4 font-display text-xl font-bold text-ink-900">{t('home.storiesTitle')}</h2>
        <ul className="flex gap-4 overflow-x-auto pb-1">
          {stories.data.map((story) => (
            <li key={`${story.kind}-${story.slug}`} className="shrink-0">
              <button
                type="button"
                onClick={() => setOpen(story)}
                className="flex w-20 flex-col items-center gap-1.5 text-center"
              >
                <span className="flex h-20 w-20 rounded-full bg-clay-500 p-[3px]">
                  <span className="flex flex-1 items-center justify-center overflow-hidden rounded-full border-[3px] border-white bg-brand-700 font-display text-xl font-bold text-white">
                    {story.image_url ? (
                      <img src={story.image_url} alt="" className="h-full w-full object-cover" loading="lazy" />
                    ) : (
                      story.name.slice(0, 1)
                    )}
                  </span>
                </span>
                <span className="line-clamp-1 w-full text-xs font-semibold text-ink-900">{story.name}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <Dialog open={open !== null} onOpenChange={(next) => (next ? null : setOpen(null))}>
        <DialogContent title={open?.name ?? ''} className="max-w-2xl">
          {open ? (
            <div className="space-y-4">
              <YouTubePlayer
                videoId={open.youtube_video_id}
                title={open.name}
                playLabel={t('home.storyPlay')}
              />
              <Link
                to={pageOf(open)}
                onClick={() => setOpen(null)}
                className="inline-flex rounded-xl bg-brand-700 px-5 py-2.5 font-semibold text-white hover:bg-brand-800"
              >
                {t('home.storyOpen')}
              </Link>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </section>
  )
}

/**
 * The reels an administrator chose, as a row of tall cards on a dark band;
 * a tap opens them full screen (`ReelPlayer`). The cards draw our own cover
 * photographs, so nothing is fetched from Instagram until a reel is opened.
 */
export function ReelsSection() {
  const { t, locale } = useI18n()
  const reels = useQuery({ queryKey: queryKeys.reels, queryFn: reelApi.list })
  const [open, setOpen] = useState<number | null>(null)
  const list = reels.data ?? []
  if (list.length === 0) return null
  return (
    <section className="bg-ink-900 py-10 text-white sm:py-12">
      <div className="container-page">
        <h2 className="mb-5 font-display text-2xl font-bold sm:text-3xl">{t('home.reelsTitle')}</h2>
        <ul className="flex gap-3 overflow-x-auto pb-2 sm:gap-4">
          {list.map((reel, index) => {
            const caption = reelCaption(reel, locale)
            return (
              <li key={reel.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => setOpen(index)}
                  aria-label={caption ?? t('reels.play')}
                  className="group relative block aspect-[9/16] w-36 overflow-hidden rounded-2xl bg-gradient-to-b from-brand-700 to-clay-600 text-start focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-wheat-500 sm:w-44"
                >
                  {reel.cover_url ? (
                    <img
                      src={reel.cover_url}
                      alt=""
                      loading="lazy"
                      className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  ) : (
                    <Instagram className="absolute start-3 top-3 h-6 w-6 text-white/80" aria-hidden="true" />
                  )}
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span className="flex h-12 w-12 items-center justify-center rounded-full bg-black/40 backdrop-blur transition-transform group-hover:scale-110">
                      <Play className="h-6 w-6 translate-x-0.5 fill-white" aria-hidden="true" />
                    </span>
                  </span>
                  {caption ? (
                    <span
                      dir="auto"
                      className="absolute inset-x-0 bottom-0 line-clamp-3 bg-gradient-to-t from-black/80 to-transparent p-3 pt-8 text-sm font-semibold leading-snug"
                    >
                      {caption}
                    </span>
                  ) : null}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
      <ReelPlayer reels={list} index={open} onIndexChange={setOpen} />
    </section>
  )
}

/**
 * The stories row filled with the reels an administrator added, as round
 * covers; a tap opens them in the full-screen player. Nothing at all while
 * there are no reels either.
 */
function ReelStories() {
  const { t, locale } = useI18n()
  const reels = useQuery({ queryKey: queryKeys.reels, queryFn: reelApi.list })
  const [open, setOpen] = useState<number | null>(null)
  const list = reels.data ?? []
  if (list.length === 0) return null
  return (
    <section className="border-b border-ink-100 bg-white py-6">
      <div className="container-page">
        <h2 className="mb-4 font-display text-xl font-bold text-ink-900">{t('home.storiesTitle')}</h2>
        <ul className="flex gap-4 overflow-x-auto pb-1">
          {list.map((reel, index) => {
            const caption = reelCaption(reel, locale)
            return (
              <li key={reel.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => setOpen(index)}
                  aria-label={caption ?? t('reels.play')}
                  className="flex w-20 flex-col items-center gap-1.5 text-center"
                >
                  <span className="flex h-20 w-20 rounded-full bg-clay-500 p-[3px]">
                    <span className="flex flex-1 items-center justify-center overflow-hidden rounded-full border-[3px] border-white bg-gradient-to-b from-brand-700 to-clay-600 text-white">
                      {reel.cover_url ? (
                        <img src={reel.cover_url} alt="" className="h-full w-full object-cover" loading="lazy" />
                      ) : (
                        <Instagram className="h-7 w-7" aria-hidden="true" />
                      )}
                    </span>
                  </span>
                  {caption ? (
                    <span dir="auto" className="line-clamp-1 w-full text-xs font-semibold text-ink-900">
                      {caption}
                    </span>
                  ) : null}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
      <ReelPlayer reels={list} index={open} onIndexChange={setOpen} />
    </section>
  )
}

export function StatsSection() {
  const t = useT()
  const stats = useQuery({ queryKey: queryKeys.publicStats, queryFn: publicBusinessApi.stats })
  if (!stats.data) return null
  const items = [
    { value: stats.data.total_businesses, label: t('home.statShops'), to: '/businesses' },
    { value: stats.data.total_products, label: t('home.statProducts'), to: '/products' },
    { value: stats.data.total_talents, label: t('home.statTalents'), to: '/services' },
  ]
  return (
    <Band tone="sand">
      <ul className="grid gap-4 sm:grid-cols-3">
        {items.map((item) => (
          <li key={item.label}>
            <Link
              to={item.to}
              className="flex flex-col rounded-2xl border border-ink-100 bg-white p-5 shadow-card hover:border-brand-300"
            >
              <span className="ltr-nums font-display text-4xl font-bold text-brand-700">{item.value}</span>
              <span className="mt-1 font-semibold text-ink-700">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Band>
  )
}

export function ProductsSection() {
  const t = useT()
  const [origin, setOrigin] = useState<GoodsOrigin | undefined>(undefined)
  const query: ProductQuery = { sort: 'newest', page_size: 8, ...(origin ? { origin } : {}) }
  const products = useQuery({
    queryKey: queryKeys.products(query),
    queryFn: () => publicItemApi.search(query),
  })
  const tabs: { value: GoodsOrigin | undefined; label: string }[] = [
    { value: undefined, label: t('home.tabAll') },
    { value: 'LOCAL', label: t('directory.originLocal') },
    { value: 'IMPORTED', label: t('onboarding.importedTitle') },
  ]
  const items = products.data?.items ?? []
  if (!origin && products.isSuccess && items.length === 0) return null
  return (
    <Band>
      <SectionHeading title={t('home.productsTitle')} to="/products" more={t('home.viewAll')} />
      <div className="mb-5 flex flex-wrap gap-2" role="group" aria-label={t('home.productsTitle')}>
        {tabs.map((tab) => (
          <button
            key={tab.label}
            type="button"
            aria-pressed={origin === tab.value}
            onClick={() => setOrigin(tab.value)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
              origin === tab.value
                ? 'bg-brand-700 text-white'
                : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </Band>
  )
}

/** At most this many category rows, busiest categories first. */
const CATEGORY_ROWS = 6

/**
 * One row of newest products per category, OLX-style: the categories with
 * the most shops first, a row only where the category has products.
 */
export function CategoryProductsSection() {
  const t = useT()
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: taxonomyApi.categories })
  const busiest = (categories.data ?? [])
    .filter((category) => category.is_active !== false && category.business_count > 0)
    .sort((a, b) => b.business_count - a.business_count)
    .slice(0, CATEGORY_ROWS)
  if (busiest.length === 0) return null
  return (
    <Band>
      <div className="space-y-10">
        {busiest.map((category) => (
          <CategoryRow key={category.id} category={category} more={t('home.viewAll')} />
        ))}
      </div>
    </Band>
  )
}

function CategoryRow({ category, more }: { category: Category; more: string }) {
  const query: ProductQuery = { category: category.slug, sort: 'newest', page_size: 8 }
  const products = useQuery({
    queryKey: queryKeys.products(query),
    queryFn: () => publicItemApi.search(query),
  })
  const items = products.data?.items ?? []
  if (items.length === 0) return null
  return (
    <section aria-labelledby={`cat-row-${category.id}`}>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 id={`cat-row-${category.id}`} className="flex items-center gap-3 font-display text-2xl font-bold text-ink-900">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
            <CategoryIcon name={category.icon} className="h-5 w-5" />
          </span>
          {category.name_ar}
        </h2>
        <Link
          to={`/products?category=${encodeURIComponent(category.slug)}`}
          className="shrink-0 text-sm font-semibold text-brand-700 hover:underline"
        >
          {more}
        </Link>
      </div>
      <ul className="flex gap-4 overflow-x-auto pb-2">
        {items.map((product) => (
          <li key={product.id} className="w-52 shrink-0 sm:w-60">
            <ProductCard product={product} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export function ShopsSection() {
  const t = useT()
  const shops = useQuery({
    queryKey: queryKeys.latestBusinesses(6),
    queryFn: () => publicBusinessApi.latest(6),
  })
  if (!shops.data || shops.data.length === 0) return null
  return (
    <Band tone="sand">
      <SectionHeading title={t('home.shopsTitle')} to="/businesses" more={t('home.viewAll')} />
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {shops.data.map((business) => (
          <BusinessCard key={business.id} business={business} />
        ))}
      </div>
    </Band>
  )
}

export function TalentsSection() {
  const t = useT()
  const talents = useQuery({
    queryKey: queryKeys.latestTalents(6),
    queryFn: () => publicTalentApi.latest(6),
  })
  if (!talents.data || talents.data.length === 0) return null
  return (
    <Band>
      <SectionHeading title={t('home.talentsTitle')} to="/services" more={t('home.viewAll')} />
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {talents.data.map((talent) => (
          <TalentCard key={talent.id} talent={talent} />
        ))}
      </div>
    </Band>
  )
}

export function NewsSection() {
  const { t, locale } = useI18n()
  const news = useQuery({
    queryKey: queryKeys.articles('NEWS'),
    queryFn: () => publicArticleApi.list('NEWS'),
  })
  const [lead, ...rest] = news.data ?? []
  if (!lead) return null
  return (
    <Band tone="sand">
      <SectionHeading title={t('home.newsTitle')} to="/news" more={t('home.viewAll')} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Link to={`/articles/${encodeURIComponent(lead.slug)}`} className="group lg:col-span-2">
          {lead.cover_url ? (
            <img
              src={lead.cover_url}
              alt=""
              loading="lazy"
              className="aspect-video w-full rounded-2xl object-cover shadow-card"
            />
          ) : null}
          <h3 className="mt-4 font-display text-2xl font-bold leading-snug text-ink-900 group-hover:text-brand-700">
            {lead.title}
          </h3>
          <p className="mt-1 text-sm text-ink-500">{formatDate(lead.published_at, locale)}</p>
        </Link>
        <ul className="space-y-4">
          {rest.slice(0, 4).map((article) => (
            <li key={article.id}>
              <Link
                to={`/articles/${encodeURIComponent(article.slug)}`}
                className="flex gap-3 border-b border-ink-100 pb-4 hover:text-brand-700"
              >
                {article.cover_url ? (
                  <img
                    src={article.cover_url}
                    alt=""
                    loading="lazy"
                    className="h-16 w-24 shrink-0 rounded-xl object-cover"
                  />
                ) : null}
                <span>
                  <span className="block font-semibold leading-snug">{article.title}</span>
                  <span className="mt-1 block text-xs text-ink-500">
                    {formatDate(article.published_at, locale)}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </Band>
  )
}
