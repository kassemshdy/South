import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

import { pageCoverApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCoverKey } from '@/types/api'
import { readRemembered, writeRemembered } from '@/utils/rememberedQuery'

/** The keys that are a video's preview rather than a page's photograph. */
export const VIDEO_POSTER_KEYS = ['home_video', 'offer_video'] as const

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
  const custom = useUploadedCover(key)
  return custom ? { src: custom, custom: true } : { src: DEFAULT_PAGE_COVER, custom: false }
}

/** The image an administrator uploaded under `key`, or null: no default. */
export function useUploadedCover(key: PageCoverKey): string | null {
  const covers = useQuery({
    queryKey: queryKeys.pageCovers,
    queryFn: pageCoverApi.all,
    staleTime: 10 * 60_000,
    // The covers this browser saw last, so a refresh does not show the
    // shipped photograph or video poster first and then swap; refetched at once.
    initialData: () =>
      readRemembered<Awaited<ReturnType<typeof pageCoverApi.all>>>('pageCovers'),
    initialDataUpdatedAt: 0,
  })
  useEffect(() => {
    if (covers.data && covers.isFetchedAfterMount) writeRemembered('pageCovers', covers.data)
  }, [covers.data, covers.isFetchedAfterMount])
  return covers.data?.[key] ?? null
}
