import type { HomeSectionId } from '@/types/api'

/** What a visitor sees until the saved order arrives: the page as it was. */
export const ORIGINAL_ORDER: HomeSectionId[] = ['cover', 'hero', 'slogan']

/**
 * The proposed home page: the current sections first, as the owners asked
 * (28 Oct 2026), then the browsing sections. Shown at `/?preview=home` for
 * the manager to review on live data, and applied in one click at
 * /admin/home-layout.
 */
export const PROPOSED_ORDER: HomeSectionId[] = [
  'cover',
  'hero',
  'slogan',
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
]

export const PREVIEW_PARAM = 'preview'
export const PREVIEW_VALUE = 'home'
