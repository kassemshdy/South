import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ImageUp, RotateCcw } from 'lucide-react'
import { useRef } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { MAX_IMAGE_BYTES } from '@/features/images/ImageManager'
import { DEFAULT_PAGE_COVER } from '@/hooks/usePageCover'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCover, PageCoverKey } from '@/types/api'
import { shrinkImage } from '@/utils/shrinkImage'

/**
 * The photograph at the top of each public page, chosen here.
 *
 * Each page is named by the heading a visitor sees on it, so there is no
 * second set of names to keep in step. A page with no photograph uploaded
 * shows the site's default; resetting one goes back to it.
 */
const PAGE_LABEL: Record<PageCoverKey, TranslationKey> = {
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
          {covers.data?.map((cover) => (
            <li key={cover.page_key}>
              <CoverRow cover={cover} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function CoverRow({ cover }: { cover: PageCover }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminPageCovers })
    // The public pages read the same covers; drop their cached copy too.
    void queryClient.invalidateQueries({ queryKey: queryKeys.pageCovers })
  }

  // The server refuses anything over 5 MB and keeps no more than 1600px of
  // it, so a camera-sized photo is shrunk here first rather than refused.
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const small = await shrinkImage(file, { maxBytes: MAX_IMAGE_BYTES })
      return adminApi.setPageCover(cover.page_key, small)
    },
    onSuccess: () => {
      refresh()
      toast.success(t('admin.pageCoversSaved'))
    },
    onError: (error) =>
      toast.error(
        t('admin.pageCoversFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })
  const reset = useMutation({
    mutationFn: () => adminApi.resetPageCover(cover.page_key),
    onSuccess: refresh,
    onError: (error) =>
      toast.error(
        t('admin.pageCoversFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const busy = upload.isPending || reset.isPending

  return (
    <Card>
      <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <img
          src={cover.image_url ?? DEFAULT_PAGE_COVER}
          alt=""
          className="h-28 w-full shrink-0 rounded-xl object-cover sm:w-64"
        />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-bold text-ink-900">{t(PAGE_LABEL[cover.page_key])}</h2>
            <Badge
              className={cover.image_url ? 'bg-olive-100 text-olive-800' : 'bg-ink-100 text-ink-700'}
            >
              {cover.image_url ? t('admin.pageCoversCustom') : t('admin.pageCoversDefault')}
            </Badge>
          </div>
          <p className="text-sm text-ink-500">{t('admin.pageCoversHint')}</p>
          <div className="flex flex-wrap gap-2">
            <input
              ref={input}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) upload.mutate(file)
                event.target.value = ''
              }}
            />
            <Button size="sm" disabled={busy} onClick={() => input.current?.click()}>
              <ImageUp className="h-4 w-4" aria-hidden="true" />
              {cover.image_url ? t('admin.pageCoversReplace') : t('admin.pageCoversUpload')}
            </Button>
            {cover.image_url ? (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => reset.mutate()}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                {t('admin.pageCoversReset')}
              </Button>
            ) : null}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
