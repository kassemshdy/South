import type { HomeSectionId } from '@/types/api'

/** What a visitor sees until the saved order arrives: the page as it was. */
export const ORIGINAL_ORDER: HomeSectionId[] = ['cover', 'hero', 'slogan']

/**
 * The proposed home page, as the owners asked when it went live (28 Oct
 * 2026): the live page's own sections first, unchanged -- the cover with the
 * site's message, the pitch with Dr Hossam's video and the two action cards,
 * the slogan band -- and every new section below them, the categories
 * above the search box. Shown at
 * `/?preview=home`, applied in one click at /admin/home-layout, where an
 * administrator then reorders or hides any of them.
 */
export const PROPOSED_ORDER: HomeSectionId[] = [
  'cover',
  'hero',
  'slogan',
  'categories',
  'search',
  'stories',
  'reels',
  'stats',
  'products',
  'top_rated_products',
  'top_viewed_products',
  'category_products',
  'shops',
  'talents',
  'workshops',
  'online_workshops',
  'news',
  'blog',
]

export const PREVIEW_PARAM = 'preview'
export const PREVIEW_VALUE = 'home'
