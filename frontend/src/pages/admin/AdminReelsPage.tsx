import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { ImageCropDialog } from '@/features/images/ImageCropDialog'
import { REEL_ASPECT } from '@/features/images/shapes'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Reel } from '@/types/api'

/**
 * Collab reels on the home page (the owners' request, 28 Oct 2026): an
 * Instagram link and a tall cover each. A reel shows publicly once it has a
 * cover and is published; opening it plays Instagram's embed.
 */
export function AdminReelsPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const reels = useQuery({ queryKey: queryKeys.adminReels, queryFn: adminApi.reels })
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [cropping, setCropping] = useState<{ reel: Reel; file: File } | null>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminReels })
    void queryClient.invalidateQueries({ queryKey: queryKeys.reels })
  }
  const failed = (error: unknown) =>
    toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined)

  const create = useMutation({
    mutationFn: () =>
      adminApi.createReel({ instagram_url: url.trim(), title: title.trim() || null, sort_order: 0 }),
    onSuccess: () => {
      setUrl('')
      setTitle('')
      refresh()
      toast.success(t('admin.correctionSaved'))
    },
    onError: failed,
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof adminApi.updateReel>[1] }) =>
      adminApi.updateReel(id, body),
    onSuccess: refresh,
    onError: failed,
  })
  const cover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => adminApi.uploadReelCover(id, file),
    onSuccess: () => {
      refresh()
      toast.success(t('admin.correctionSaved'))
    },
    onError: failed,
  })
  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteReel(id),
    onSuccess: refresh,
    onError: failed,
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (url.trim()) create.mutate()
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.reelsTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.reelsHint')}</p>
      </header>

      <Card>
        <CardBody>
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[2fr_1fr_auto] sm:items-end">
            <label className="block">
              <span className="mb-1 block text-sm font-semibold">{t('admin.reelUrl')}</span>
              <Input
                type="url"
                dir="ltr"
                required
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://www.instagram.com/reel/…"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-semibold">{t('admin.reelTitle')}</span>
              <Input value={title} maxLength={160} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <Button type="submit" loading={create.isPending}>
              {t('admin.reelAdd')}
            </Button>
          </form>
        </CardBody>
      </Card>

      {reels.isLoading ? (
        <InlineSpinner />
      ) : reels.isError ? (
        <ErrorState error={reels.error} onRetry={() => void reels.refetch()} />
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {(reels.data ?? []).map((reel) => (
            <li key={reel.id}>
              <Card className="overflow-hidden">
                <div className="aspect-[9/16] bg-sand-100">
                  {reel.cover_url ? (
                    <img src={reel.cover_url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <span className="flex h-full items-center justify-center p-4 text-center text-sm text-ink-500">
                      {t('admin.reelNeedsCover')}
                    </span>
                  )}
                </div>
                <CardBody className="space-y-3 p-3">
                  <a
                    href={`https://www.instagram.com/${reel.instagram_kind}/${encodeURIComponent(reel.instagram_code)}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block truncate text-sm font-semibold text-brand-700 hover:underline"
                  >
                    {reel.title ?? reel.instagram_code}
                  </a>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={reel.is_published}
                      onChange={() =>
                        update.mutate({ id: reel.id, body: { is_published: !reel.is_published } })
                      }
                      className="h-4 w-4 accent-brand-700"
                    />
                    {t('admin.reelPublished')}
                  </label>
                  <div className="flex gap-2">
                    <label className="inline-flex flex-1 cursor-pointer items-center justify-center gap-1 rounded-lg px-2 py-2 text-sm font-semibold ring-1 ring-ink-100 hover:bg-sand-100">
                      <ImagePlus className="h-4 w-4" aria-hidden="true" />
                      {t('admin.reelCover')}
                      <input
                        type="file"
                        accept="image/*"
                        className="sr-only"
                        onChange={(event) => {
                          const file = event.target.files?.[0]
                          event.target.value = ''
                          if (file) setCropping({ reel, file })
                        }}
                      />
                    </label>
                    <button
                      type="button"
                      aria-label={t('common.delete')}
                      onClick={() => {
                        if (window.confirm(t('admin.reelDeleteConfirm'))) remove.mutate(reel.id)
                      }}
                      className="flex h-9 w-9 items-center justify-center rounded-lg text-clay-700 ring-1 ring-ink-100 hover:bg-clay-50"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <ImageCropDialog
        file={cropping?.file ?? null}
        aspect={REEL_ASPECT}
        onCancel={() => setCropping(null)}
        onCropped={(file) => {
          if (cropping) cover.mutate({ id: cropping.reel.id, file })
          setCropping(null)
        }}
      />
    </div>
  )
}
