import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, ExternalLink, ImagePlus, Trash2 } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { EmptyState, ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { ProviderIcon } from '@/features/home/ReelPlayer'
import { useCropStep } from '@/features/images/ImageCropDialog'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminReel, ReelInput } from '@/types/api'

const EMPTY: ReelInput = { url: '', caption_ar: null, caption_en: null, is_published: false }

/**
 * The home page's short videos -- YouTube Shorts or Instagram reels: paste a
 * link, add a caption (a Short brings its own cover; one can be uploaded),
 * publish, and put them in order. A reel is saved hidden unless "shown" is
 * ticked, and the row appears on the home page only once its section is
 * switched on at /admin/home-layout.
 */
export function AdminReelsPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const reels = useQuery({ queryKey: queryKeys.adminReels, queryFn: adminApi.reels })

  const refreshed = (list: AdminReel[]) => {
    queryClient.setQueryData(queryKeys.adminReels, list)
    void queryClient.invalidateQueries({ queryKey: queryKeys.reels })
  }
  const failed = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const add = useMutation({
    mutationFn: adminApi.addReel,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminReels })
      void queryClient.invalidateQueries({ queryKey: queryKeys.reels })
      toast.success(t('wizard.saved'))
    },
    onError: failed,
  })
  const reorder = useMutation({
    mutationFn: adminApi.reorderReels,
    onSuccess: refreshed,
    onError: failed,
  })

  const list = reels.data ?? []
  const move = (index: number, by: -1 | 1) => {
    const ids = list.map((reel) => reel.id)
    const target = index + by
    if (target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target]!, ids[index]!]
    reorder.mutate(ids)
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.reelsTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.reelsHint')}</p>
      </header>

      <Card>
        <CardBody>
          <h2 className="mb-4 text-xl font-bold">{t('admin.reelAdd')}</h2>
          <ReelForm
            initial={EMPTY}
            submitLabel={t('admin.reelAdd')}
            pending={add.isPending}
            resetOnSave
            onSave={(values) => add.mutateAsync(values)}
          />
        </CardBody>
      </Card>

      {reels.isLoading ? (
        <InlineSpinner />
      ) : reels.isError ? (
        <ErrorState error={reels.error} onRetry={() => void reels.refetch()} />
      ) : list.length === 0 ? (
        <EmptyState title={t('admin.reelsEmpty')} />
      ) : (
        <ol className="space-y-4">
          {list.map((reel, index) => (
            <li key={reel.id}>
              <ReelRow
                reel={reel}
                first={index === 0}
                last={index === list.length - 1}
                moving={reorder.isPending}
                onMove={(by) => move(index, by)}
                onDeleted={refreshed}
              />
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function ReelRow({
  reel,
  first,
  last,
  moving,
  onMove,
  onDeleted,
}: {
  reel: AdminReel
  first: boolean
  last: boolean
  moving: boolean
  onMove: (by: -1 | 1) => void
  onDeleted: (remaining: AdminReel[]) => void
}) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const coverCrop = useCropStep('reel')

  const saved = (next: AdminReel) => {
    queryClient.setQueryData<AdminReel[]>(queryKeys.adminReels, (previous) =>
      previous?.map((entry) => (entry.id === next.id ? next : entry)),
    )
    void queryClient.invalidateQueries({ queryKey: queryKeys.reels })
    toast.success(t('wizard.saved'))
  }
  const failed = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const update = useMutation({
    mutationFn: (values: ReelInput) => adminApi.updateReel(reel.id, values),
    onSuccess: saved,
    onError: failed,
  })
  const cover = useMutation({
    mutationFn: (file: File) => adminApi.setReelCover(reel.id, file),
    onSuccess: saved,
    onError: failed,
  })
  const removeCover = useMutation({
    mutationFn: () => adminApi.removeReelCover(reel.id),
    onSuccess: saved,
    onError: failed,
  })
  const remove = useMutation({
    mutationFn: () => adminApi.deleteReel(reel.id),
    onSuccess: (remaining) => {
      onDeleted(remaining)
      toast.success(t('admin.reelDeleted'))
    },
    onError: failed,
  })

  const moveButton =
    'flex h-10 w-10 items-center justify-center rounded-lg ring-1 ring-ink-100 hover:bg-sand-100 disabled:opacity-40'

  return (
    <Card>
      <CardBody className="flex flex-col gap-5 sm:flex-row">
        {coverCrop.dialog}
        <div className="flex shrink-0 flex-row items-start gap-3 sm:flex-col">
          <div className="relative aspect-[9/16] w-24 overflow-hidden rounded-xl bg-gradient-to-b from-brand-700 to-clay-600">
            {reel.cover_url ? (
              <img src={reel.cover_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <ProviderIcon provider={reel.provider} className="absolute start-2 top-2 h-5 w-5 text-white/80" />
            )}
          </div>
          <div className="flex flex-col gap-2">
            <input
              ref={input}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              aria-label={t('admin.reelCover')}
              onChange={(event) => {
                const file = event.target.files?.[0]
                event.target.value = ''
                if (!file) return
                void coverCrop.crop(file).then((cropped) => {
                  if (cropped) cover.mutate(cropped)
                })
              }}
            />
            <Button size="sm" variant="outline" loading={cover.isPending} onClick={() => input.current?.click()}>
              <ImagePlus className="h-4 w-4" aria-hidden="true" />
              {t('admin.reelCover')}
            </Button>
            {reel.cover_url ? (
              <Button size="sm" variant="ghost" loading={removeCover.isPending} onClick={() => removeCover.mutate()}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {t('admin.reelRemoveCover')}
              </Button>
            ) : null}
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <a
              href={reel.url}
              target="_blank"
              rel="noopener noreferrer"
              dir="ltr"
              className="inline-flex min-w-0 items-center gap-1 truncate text-sm font-semibold text-brand-700 hover:underline"
            >
              <ExternalLink className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">{reel.url}</span>
            </a>
            <div className="flex gap-2">
              <button
                type="button"
                aria-label={t('admin.moveUp')}
                disabled={first || moving}
                onClick={() => onMove(-1)}
                className={moveButton}
              >
                <ArrowUp className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={t('admin.moveDown')}
                disabled={last || moving}
                onClick={() => onMove(1)}
                className={moveButton}
              >
                <ArrowDown className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
          <ReelForm
            initial={{
              url: reel.url,
              caption_ar: reel.caption_ar,
              caption_en: reel.caption_en,
              is_published: reel.is_published,
            }}
            submitLabel={t('common.save')}
            pending={update.isPending}
            onSave={(values) => update.mutateAsync(values)}
          />
          <Button
            size="sm"
            variant="ghost"
            loading={remove.isPending}
            onClick={() => {
              if (window.confirm(t('admin.reelDeleteConfirm'))) remove.mutate()
            }}
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t('common.delete')}
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}

function ReelForm({
  initial,
  submitLabel,
  pending,
  resetOnSave,
  onSave,
}: {
  initial: ReelInput
  submitLabel: string
  pending: boolean
  resetOnSave?: boolean
  onSave: (values: ReelInput) => Promise<unknown>
}) {
  const t = useT()
  const [url, setUrl] = useState(initial.url)
  const [captionAr, setCaptionAr] = useState(initial.caption_ar ?? '')
  const [captionEn, setCaptionEn] = useState(initial.caption_en ?? '')
  const [published, setPublished] = useState(initial.is_published)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSave({
      url: url.trim(),
      caption_ar: captionAr.trim() || null,
      caption_en: captionEn.trim() || null,
      is_published: published,
    })
      .then(() => {
        if (!resetOnSave) return
        setUrl('')
        setCaptionAr('')
        setCaptionEn('')
        setPublished(false)
      })
      // The mutation's own onError has already said what went wrong.
      .catch(() => undefined)
  }

  return (
    <form className="space-y-3" onSubmit={submit}>
      <Field label={t('admin.reelUrl')} hint={t('admin.reelUrlHint')} required>
        {(props) => (
          <Input
            {...props}
            dir="ltr"
            inputMode="url"
            required
            maxLength={500}
            placeholder="https://youtube.com/shorts/…"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        )}
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t('admin.reelCaptionAr')}>
          {(props) => (
            <Textarea
              {...props}
              dir="rtl"
              rows={2}
              maxLength={300}
              value={captionAr}
              onChange={(event) => setCaptionAr(event.target.value)}
            />
          )}
        </Field>
        <Field label={t('admin.reelCaptionEn')}>
          {(props) => (
            <Textarea
              {...props}
              dir="ltr"
              rows={2}
              maxLength={300}
              value={captionEn}
              onChange={(event) => setCaptionEn(event.target.value)}
            />
          )}
        </Field>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm font-semibold text-ink-700">
          <input
            type="checkbox"
            checked={published}
            onChange={(event) => setPublished(event.target.checked)}
            className="h-5 w-5 accent-brand-700"
          />
          {t('admin.reelPublished')}
        </label>
        <Button type="submit" size="sm" loading={pending}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
