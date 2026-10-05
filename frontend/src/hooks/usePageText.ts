import { useQuery } from '@tanstack/react-query'

import { useI18n } from '@/i18n'
import { pageApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageKey } from '@/types/api'

export interface PageTextFields {
  title: string | null
  summary: string | null
  body: string | null
  /** Settled: either the administrator's text has arrived or there is none. */
  ready: boolean
}

/**
 * A static page's administrator-written text in the reader's language. Each
 * field is null where the administrator wrote nothing, and the caller shows
 * its built-in catalog text in its place -- so a request that fails, or a
 * page nobody has edited, still reads exactly as it shipped.
 *
 * Cached for the visit: the footer reads the about page's summary on every
 * page.
 */
export function usePageText(key: PageKey): PageTextFields {
  const { locale } = useI18n()
  const query = useQuery({
    queryKey: queryKeys.page(key),
    queryFn: () => pageApi.get(key),
    staleTime: 10 * 60_000,
  })
  const page = query.data
  return {
    title: (locale === 'ar' ? page?.title_ar : page?.title_en) ?? null,
    summary: (locale === 'ar' ? page?.summary_ar : page?.summary_en) ?? null,
    body: (locale === 'ar' ? page?.body_ar : page?.body_en) ?? null,
    ready: !query.isPending,
  }
}
