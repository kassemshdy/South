import { useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { ImagePlus, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { EmptyState, ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_BYTES } from '@/features/images/ImageManager'
import { useCropStep } from '@/features/images/ImageCropDialog'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import type { Story, StoryStatus } from '@/types/api'
import { formatDateTime } from '@/utils/format'

const STATUS_KEYS: Record<StoryStatus, TranslationKey> = {
  PENDING_REVIEW: 'stories.statusPending',
  APPROVED: 'stories.statusShowing',
  REJECTED: 'stories.statusRejected',
}

const STATUS_TONE: Record<StoryStatus, string> = {
  PENDING_REVIEW: 'bg-wheat-100 text-ink-900',
  APPROVED: 'bg-brand-100 text-brand-800',
  REJECTED: 'bg-clay-100 text-clay-800',
}

/**
 * An owner's photo stories, for a shop or a service profile: post a photo,
 * see whether it is waiting, showing (and until when) or refused, and take
 * one down. The listing is decided by the functions passed in, which call
 * the owner's own routes -- never an id the page could be talked into.
 */
export function StoryManager({
  queryKey,
  list,
  post,
  remove,
}: {
  queryKey: QueryKey
  list: () => Promise<Story[]>
  post: (file: File, caption: string | null) => Promise<Story>
  remove: (id: string) => Promise<Story[]>
}) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const crop = useCropStep('story')
  const [caption, setCaption] = useState('')
  const stories = useQuery({ queryKey, queryFn: list })

  const failed = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const upload = useMutation({
    mutationFn: (file: File) => post(file, caption.trim() || null),
    onSuccess: () => {
      setCaption('')
      void queryClient.invalidateQueries({ queryKey })
      toast.success(t('stories.posted'), t('stories.postedHint'))
    },
    onError: failed,
  })
  const drop = useMutation({
    mutationFn: remove,
    onSuccess: (remaining) => {
      queryClient.setQueryData(queryKey, remaining)
      void queryClient.invalidateQueries({ queryKey: ['home', 'stories'] })
    },
    onError: failed,
  })

  const pick = async (picked: File | undefined) => {
    if (!picked) return
    if (!ACCEPTED_IMAGE_TYPES.split(',').includes(picked.type)) {
      toast.error(t('images.badType'), t('images.badTypeDescription'))
      return
    }
    const file = await crop.crop(picked)
    if (!file) return
    if (file.size > MAX_IMAGE_BYTES) {
      toast.error(t('images.tooLarge'), t('images.tooLargeDescription'))
      return
    }
    upload.mutate(file)
  }

  return (
    <div className="space-y-6">
      {crop.dialog}
      <div>
        <h3 className="font-bold">{t('stories.ownerTitle')}</h3>
        <p className="mt-1 text-sm text-ink-500">{t('stories.ownerHint')}</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Field label={t('stories.caption')} className="flex-1">
          {(props) => (
            <Input
              {...props}
              dir="auto"
              maxLength={200}
              value={caption}
              onChange={(event) => setCaption(event.target.value)}
            />
          )}
        </Field>
        <input
          ref={input}
          type="file"
          accept={ACCEPTED_IMAGE_TYPES}
          className="sr-only"
          aria-label={t('stories.add')}
          onChange={(event) => {
            const file = event.target.files?.[0]
            event.target.value = ''
            void pick(file)
          }}
        />
        <Button type="button" loading={upload.isPending} onClick={() => input.current?.click()}>
          <ImagePlus className="h-4 w-4" aria-hidden="true" />
          {t('stories.add')}
        </Button>
      </div>

      {stories.isLoading ? (
        <InlineSpinner />
      ) : stories.isError ? (
        <ErrorState error={stories.error} onRetry={() => void stories.refetch()} />
      ) : (stories.data ?? []).length === 0 ? (
        <EmptyState title={t('stories.empty')} />
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(stories.data ?? []).map((story) => (
            <li key={story.id} className="overflow-hidden rounded-xl border border-ink-100 bg-white">
              <div className="relative aspect-[9/16] bg-ink-900">
                <img src={story.image_url} alt={story.caption ?? ''} className="h-full w-full object-cover" />
                <Badge className={`absolute start-2 top-2 ${STATUS_TONE[story.status]}`}>
                  {t(STATUS_KEYS[story.status])}
                </Badge>
              </div>
              <div className="space-y-2 p-2.5 text-sm">
                {story.caption ? (
                  <p dir="auto" className="line-clamp-2 font-semibold text-ink-900">
                    {story.caption}
                  </p>
                ) : null}
                {story.status === 'APPROVED' && story.expires_at ? (
                  <p className="text-xs text-ink-500">
                    {t('stories.until', { time: formatDateTime(story.expires_at, locale) })}
                  </p>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  loading={drop.isPending && drop.variables === story.id}
                  onClick={() => {
                    if (window.confirm(t('stories.deleteConfirm'))) drop.mutate(story.id)
                  }}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  {t('common.delete')}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
