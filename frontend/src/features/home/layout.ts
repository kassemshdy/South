import type { HomeSectionId } from '@/types/api'

/** What a visitor sees until the saved order arrives: the page as it was. */
export const ORIGINAL_ORDER: HomeSectionId[] = ['cover', 'hero', 'slogan']

/**
 * The proposed e-commerce home page: browsing first, the original pitch
 * kept below it. Shown at `/?preview=home` for the manager to review on
 * live data, and applied in one click at /admin/home-layout.
 */
export const PROPOSED_ORDER: HomeSectionId[] = [
  'search',
  'categories',
  'stories',
  'cover',
  'hero',
  'stats',
  'products',
  'category_products',
  'shops',
  'talents',
  'news',
  'slogan',
]

export const PREVIEW_PARAM = 'preview'
export const PREVIEW_VALUE = 'home'
