import { useQuery } from '@tanstack/react-query'

import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { CoverUpload } from '@/features/admin/CoverUpload'
import { DEFAULT_PAGE_COVER, VIDEO_POSTER_KEYS } from '@/hooks/usePageCover'
import { useT, type TranslationKey } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCoverKey } from '@/types/api'

/**
 * The photograph at the top of each public page, chosen here.
 *
 * Each page is named by the heading a visitor sees on it, so there is no
 * second set of names to keep in step. A page with no photograph uploaded
 * shows the site's default; resetting one goes back to it.
 */
const PAGE_LABEL: Record<Exclude<PageCoverKey, (typeof VIDEO_POSTER_KEYS)[number]>, TranslationKey> = {
  home: 'nav.home',
  offer: 'offerPage.title',
  browse: 'browsePage.title',
  products: 'products.heading',
  products_local: 'onboarding.ownerTitle',
  products_imported: 'products.importedPageTitle',
  talent: 'nav.services',
  jobs: 'nav.jobs',
  contact: 'nav.contact',
}

export function AdminPageCoversPage() {
  const t = useT()
  const covers = useQuery({ queryKey: queryKeys.adminPageCovers, queryFn: adminApi.pageCovers })

  return (
    <div className="max-w-4xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.pageCoversHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.pageCoversSubtitle')}</p>
      </header>

      {covers.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : covers.isError ? (
        <ErrorState error={covers.error} onRetry={() => void covers.refetch()} />
      ) : (
        <ul className="space-y-4">
          {/* Video previews are set beside their video, in the site settings. */}
          {covers.data?.map((cover) =>
            cover.page_key === 'home_video' || cover.page_key === 'offer_video' ? null : (
              <li key={cover.page_key}>
                <CoverUpload
                  cover={cover}
                  title={t(PAGE_LABEL[cover.page_key])}
                  hint={t('admin.pageCoversHint')}
                  fallbackSrc={DEFAULT_PAGE_COVER}
                  resetLabel={t('admin.pageCoversReset')}
                />
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  )
}
