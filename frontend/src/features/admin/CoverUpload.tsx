import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUp, RotateCcw } from 'lucide-react'
import { useRef } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { MAX_IMAGE_BYTES } from '@/features/images/ImageManager'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageCover } from '@/types/api'
import { shrinkImage } from '@/utils/shrinkImage'

interface CoverUploadProps {
  cover: PageCover
  title: string
  hint: string
  /** What shows with nothing uploaded; null draws an empty brand panel. */
  fallbackSrc: string | null
  /** The remove button's words: "back to the default" or "remove". */
  resetLabel: string
}

/**
 * One uploadable image keyed in page covers: a page's top photograph, or a
 * video's preview. Upload replaces it; reset deletes it, and the page goes
 * back to `fallbackSrc`.
 */
export function CoverUpload({ cover, title, hint, fallbackSrc, resetLabel }: CoverUploadProps) {
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
  const shown = cover.image_url ?? fallbackSrc

  return (
    <Card>
      <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {shown ? (
          <img
            src={shown}
            alt=""
            className="h-28 w-full shrink-0 rounded-xl object-cover sm:w-64"
          />
        ) : (
          <div className="h-28 w-full shrink-0 rounded-xl bg-brand-900 sm:w-64" aria-hidden="true" />
        )}
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-bold text-ink-900">{title}</h2>
            <Badge
              className={cover.image_url ? 'bg-olive-100 text-olive-800' : 'bg-ink-100 text-ink-700'}
            >
              {cover.image_url ? t('admin.pageCoversCustom') : t('admin.pageCoversDefault')}
            </Badge>
          </div>
          <p className="text-sm text-ink-500">{hint}</p>
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
            <Button
              type="button"
              size="sm"
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              <ImageUp className="h-4 w-4" aria-hidden="true" />
              {cover.image_url ? t('admin.pageCoversReplace') : t('admin.pageCoversUpload')}
            </Button>
            {cover.image_url ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => reset.mutate()}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                {resetLabel}
              </Button>
            ) : null}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
