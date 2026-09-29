import { useQuery } from '@tanstack/react-query'

import { pageCoverApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCoverKey } from '@/types/api'

/** The photograph every page shows until an administrator replaces it. */
export const DEFAULT_PAGE_COVER = '/south-hills.jpg'

/**
 * A page's cover photograph: the one an administrator uploaded for it, or
 * the default. One request for all pages, cached for the visit, so moving
 * between pages does not refetch.
 *
 * `custom` says which it is, because the default's alt text describes that
 * particular photograph and would be wrong over any other.
 */
export function usePageCover(key: PageCoverKey): { src: string; custom: boolean } {
  const covers = useQuery({
    queryKey: queryKeys.pageCovers,
    queryFn: pageCoverApi.all,
    staleTime: 10 * 60_000,
  })
  const custom = covers.data?.[key]
  return custom ? { src: custom, custom: true } : { src: DEFAULT_PAGE_COVER, custom: false }
}
