import type { BusinessQuery, BusinessStatus } from '@/types/api'

/** Central query-key registry so invalidation targets stay consistent. */
export const queryKeys = {
  me: ['me'] as const,
  myVerificationDocument: ['me', 'verification-document'] as const,
  categories: ['categories'] as const,
  locations: ['locations'] as const,
  businesses: (query: BusinessQuery) => ['businesses', query] as const,
  latestBusinesses: (limit: number) => ['businesses', 'latest', limit] as const,
  publicStats: ['businesses', 'stats'] as const,
  business: (slug: string) => ['business', slug] as const,
  myBusinesses: ['my-businesses'] as const,
  myBusiness: (id: string) => ['my-business', id] as const,
  myBusinessItems: (id: string) => ['my-business', id, 'items'] as const,
  readiness: (id: string) => ['my-business', id, 'readiness'] as const,
  adminStats: ['admin', 'stats'] as const,
  adminBusinesses: (status: BusinessStatus | undefined, page: number, q?: string) =>
    ['admin', 'businesses', status ?? 'all', page, q ?? ''] as const,
  adminBusiness: (id: string) => ['admin', 'business', id] as const,
  adminUsers: (page: number) => ['admin', 'users', page] as const,
  adminCategories: ['admin', 'categories'] as const,
  adminLocations: ['admin', 'locations'] as const,
}
