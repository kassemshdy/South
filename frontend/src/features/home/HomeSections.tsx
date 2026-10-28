/**
 * The browsing sections of the home page (the owners' request, 27 Oct
 * 2026): search, categories, stories, short videos, live counts, newest
 * products, shops, services and news. Each is one self-contained section an administrator
 * can move or hide at /admin/home-layout; each renders nothing while it has
 * nothing to show, so an empty one never leaves a heading over a blank.
 *
 * They reuse the directories' own cards and queries, so a product looks the
 * same here as on /products and shares its cache.
 */

import { useQuery } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { CategoryIcon } from '@/features/home/categoryIcon'
import { ProviderIcon, ReelPlayer, reelCaption } from '@/features/home/ReelPlayer'
import { StoryViewer } from '@/features/home/StoryViewer'
import { SearchBox } from '@/features/search/SearchBox'
import { ProductCard } from '@/features/items/ProductCard'
import { WORK_MODE_KEYS } from '@/features/talent/labels'
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
import type { ArticleSection, Category, GoodsOrigin, ProductQuery } from '@/types/api'
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

/** The search box on its band, suggesting as someone types (`SearchBox`). */
export function SearchSection() {
  return (
    <section className="bg-brand-700 py-6 sm:py-8">
      <div className="container-page">
        <SearchBox />
      </div>
    </section>
  )
}

/** What four rows hold at the narrowest width; past it some are cut. */
const CATEGORY_GRID_SMALLEST = 4 * 3

export function CategoriesSection() {
  const t = useT()
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: taxonomyApi.categories })
  // Only categories with products on sale, the fullest first.
  const list = (categories.data ?? [])
    .filter((category) => category.is_active !== false && category.item_count > 0)
    .sort((a, b) => b.item_count - a.item_count)
  if (list.length === 0) return null
  return (
    <Band>
      <SectionHeading
        title={t('home.categoriesTitle')}
        to={list.length > CATEGORY_GRID_SMALLEST ? '/products' : undefined}
        more={t('home.viewAll')}
      />
      {/* Every card is one fixed height, so the height cap shows four whole
          rows at any width and cuts the rest. */}
      <ul className="grid max-h-[42.25rem] auto-rows-[10rem] grid-cols-3 gap-3 overflow-hidden sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
        {list.map((category) => (
          <li key={category.id}>
            <Link
              to={`/products?category=${encodeURIComponent(category.slug)}`}
              className="flex h-full flex-col items-center gap-2 rounded-2xl border border-ink-100 bg-white p-3 text-center shadow-card transition-colors hover:border-brand-300"
            >
              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                <CategoryIcon name={category.icon} className="h-7 w-7" />
              </span>
              <span className="line-clamp-2 text-sm font-semibold leading-snug text-ink-900">{category.name_ar}</span>
              <span className="ltr-nums mt-auto text-xs text-ink-500">{category.item_count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Band>
  )
}

/**
 * Photo stories, one circle per listing: the shop's logo or the person's
 * photo in a coloured ring, opening its photos full screen (`StoryViewer`).
 * While no story is showing, the row shows the shops that have a logo
 * instead, each opening its page (the owners' decisions, 28 Oct 2026).
 */
export function StoriesSection() {
  const t = useT()
  const stories = useQuery({ queryKey: queryKeys.homeStories, queryFn: homeApi.stories })
  const [open, setOpen] = useState<number | null>(null)
  if (!stories.isSuccess) return null
  if (stories.data.length === 0) return <ShopLogoRow />
  return (
    <StoryRow title={t('home.storiesTitle')}>
      {stories.data.map((group, index) => (
        <li key={`${group.kind}-${group.slug}`} className="shrink-0">
          <button
            type="button"
            onClick={() => setOpen(index)}
            className="flex w-20 flex-col items-center gap-1.5 text-center"
          >
            <StoryCircle image={group.image_url} name={group.name} ring="bg-clay-500" />
            <span dir="auto" className="line-clamp-1 w-full text-xs font-semibold text-ink-900">
              {group.name}
            </span>
          </button>
        </li>
      ))}
      <StoryViewer groups={stories.data} group={open} onGroupChange={setOpen} />
    </StoryRow>
  )
}

function ShopLogoRow() {
  const t = useT()
  const shops = useQuery({
    queryKey: queryKeys.latestBusinesses(24),
    queryFn: () => publicBusinessApi.latest(24),
  })
  const list = (shops.data ?? []).filter((business) => business.logo_url)
  if (list.length === 0) return null
  return (
    <StoryRow title={t('home.storiesTitle')}>
      {list.map((business) => (
        <li key={business.id} className="shrink-0">
          <Link
            to={`/business/${encodeURIComponent(business.slug)}`}
            className="flex w-20 flex-col items-center gap-1.5 text-center"
          >
            <StoryCircle
              image={business.logo_thumb_url ?? business.logo_url}
              name={business.name}
              ring="bg-sand-300"
            />
            <span dir="auto" className="line-clamp-1 w-full text-xs font-semibold text-ink-900">
              {business.name}
            </span>
          </Link>
        </li>
      ))}
    </StoryRow>
  )
}

function StoryRow({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-ink-100 bg-white py-6">
      <div className="container-page">
        <h2 className="mb-4 font-display text-xl font-bold text-ink-900">{title}</h2>
        <ul className="flex gap-4 overflow-x-auto pb-1">{children}</ul>
      </div>
    </section>
  )
}

function StoryCircle({ image, name, ring }: { image: string | null; name: string; ring: string }) {
  return (
    <span className={cn('flex h-20 w-20 rounded-full p-[3px]', ring)}>
      <span className="flex flex-1 items-center justify-center overflow-hidden rounded-full border-[3px] border-white bg-brand-700 font-display text-xl font-bold text-white">
        {image ? (
          <img src={image} alt="" className="h-full w-full object-cover" loading="lazy" />
        ) : (
          name.trim().slice(0, 1)
        )}
      </span>
    </span>
  )
}

/**
 * The reels an administrator chose, as a row of tall cards on a dark band;
 * a tap opens them full screen (`ReelPlayer`). The cards draw our own cover
 * photographs, so nothing is fetched from YouTube or Instagram until a reel
 * is opened.
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
                    <ProviderIcon provider={reel.provider} className="absolute start-3 top-3 h-6 w-6 text-white/80" />
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
    .filter((category) => category.is_active !== false && category.item_count > 0)
    .sort((a, b) => b.item_count - a.item_count)
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

/** Shops on the home page: the newest with a logo, as small logo cards. */
const SHOPS_SHOWN = 8

export function ShopsSection() {
  const t = useT()
  // The API's own cap; enough that eight with a logo are usually among them.
  const shops = useQuery({
    queryKey: queryKeys.latestBusinesses(24),
    queryFn: () => publicBusinessApi.latest(24),
  })
  const list = (shops.data ?? []).filter((business) => business.logo_url).slice(0, SHOPS_SHOWN)
  if (list.length === 0) return null
  return (
    <Band tone="sand">
      <SectionHeading title={t('home.shopsTitle')} to="/businesses" more={t('home.viewAll')} />
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {list.map((business) => {
          const category =
            business.category?.slug === 'other' && business.custom_category_text
              ? business.custom_category_text
              : business.category?.name_ar
          return (
            <li key={business.id}>
              <Link
                to={`/business/${encodeURIComponent(business.slug)}`}
                // Logo above the name on a phone, beside it from sm up.
                className="flex h-full flex-col items-center gap-2 rounded-2xl border border-ink-100 bg-white p-3 text-center shadow-card transition-shadow hover:shadow-lift sm:flex-row sm:gap-3 sm:text-start"
              >
                <img
                  src={business.logo_thumb_url ?? business.logo_url ?? ''}
                  alt=""
                  loading="lazy"
                  className="h-14 w-14 shrink-0 rounded-xl border border-ink-100 bg-sand-50 object-cover"
                />
                <span className="flex min-w-0 max-w-full flex-col" dir="auto">
                  <span className="line-clamp-2 text-sm font-bold leading-snug text-ink-900">{business.name}</span>
                  <span className="truncate text-xs text-ink-500">
                    {[category, business.location?.name_ar].filter(Boolean).join(' · ')}
                  </span>
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </Band>
  )
}

/**
 * People offering a trade, drawn without their photograph: an initial in a
 * circle, the trade, where and how they work, and a button to ask for it.
 */
export function TalentsSection() {
  const t = useT()
  const talents = useQuery({
    queryKey: queryKeys.latestTalents(8),
    queryFn: () => publicTalentApi.latest(8),
  })
  if (!talents.data || talents.data.length === 0) return null
  return (
    <section className="py-10 sm:py-12">
      <div className="container-page">
        <div className="rounded-3xl bg-brand-50 p-5 sm:p-7">
          <SectionHeading title={t('home.talentsTitle')} to="/services" more={t('home.viewAll')} />
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {talents.data.map((talent) => {
              const skill =
                talent.skill?.slug === 'other' && talent.custom_skill_text
                  ? talent.custom_skill_text
                  : talent.skill?.name_ar
              const where = [
                talent.location?.name_ar,
                talent.work_mode ? t(WORK_MODE_KEYS[talent.work_mode]) : null,
              ].filter(Boolean)
              const page = `/talent/${encodeURIComponent(talent.slug)}`
              return (
                <li key={talent.id} className="flex flex-col gap-3 rounded-2xl bg-white p-4" dir="auto">
                  <div className="flex items-center gap-3">
                    <span
                      aria-hidden="true"
                      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-brand-600 font-display text-lg font-bold text-white"
                    >
                      {talent.display_name.trim().slice(0, 1)}
                    </span>
                    <span className="flex min-w-0 flex-col">
                      <Link to={page} className="truncate font-bold text-ink-900 hover:text-brand-700">
                        {talent.display_name}
                      </Link>
                      {skill ? <span className="truncate text-sm font-semibold text-brand-600">{skill}</span> : null}
                    </span>
                  </div>
                  {where.length > 0 ? <span className="text-sm text-ink-500">{where.join(' · ')}</span> : null}
                  <Link
                    to={page}
                    className="mt-auto rounded-xl bg-brand-700 px-4 py-2.5 text-center font-semibold text-white hover:bg-brand-800"
                  >
                    {t('home.talentRequest')}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function NewsSection() {
  return <ArticlesSection section="NEWS" />
}

export function BlogSection() {
  return <ArticlesSection section="BLOG" />
}

/** The latest articles of one section; nothing at all while it has none. */
function ArticlesSection({ section }: { section: ArticleSection }) {
  const { t, locale } = useI18n()
  const news = useQuery({
    queryKey: queryKeys.articles(section),
    queryFn: () => publicArticleApi.list(section),
  })
  const [lead, ...rest] = news.data ?? []
  if (!lead) return null
  return (
    <Band tone="sand">
      <SectionHeading
        title={t(section === 'NEWS' ? 'nav.news' : 'blog.title')}
        to={section === 'NEWS' ? '/news' : '/blog'}
        more={t('home.viewAll')}
      />
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
