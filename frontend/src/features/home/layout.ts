import type { HomeSectionId } from '@/types/api'

/** What a visitor sees until the saved order arrives: the page as it was. */
export const ORIGINAL_ORDER: HomeSectionId[] = ['cover', 'hero', 'slogan']

/**
 * The proposed home page, in the owners' order (28 Oct 2026): the cover
 * with the site's message, the pitch with Dr Hossam's video and the two
 * action cards, then search and categories and the browsing sections; the
 * slogan band closes the page. Shown at `/?preview=home` for
 * the manager to review on live data, and applied in one click at
 * /admin/home-layout.
 */
export const PROPOSED_ORDER: HomeSectionId[] = [
  'cover',
  'hero',
  'search',
  'categories',
  'stories',
  'stats',
  'products',
  'category_products',
  'shops',
  'talents',
  'news',
  'blog',
  'slogan',
]

export const PREVIEW_PARAM = 'preview'
export const PREVIEW_VALUE = 'home'
