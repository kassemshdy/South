import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { useToast } from '@/components/ui/Toast'
import {
  ACCEPTED_IMAGE_TYPES,
  MAX_IMAGE_BYTES,
  SingleImageSlot,
  UploadButton,
} from '@/features/images/ImageManager'
import { useCropStep } from '@/features/images/ImageCropDialog'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { ownerTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ImageKind, OwnerTalent } from '@/types/api'

/**
 * The profile photo is stored as an `ImageKind.LOGO` row — a profile has no
 * "logo" of its own, and reusing that kind gets the square 600px variant the
 * headshot wants without a new enum value.
 */
const PHOTO_KIND = 'LOGO' as const
const COVER_KIND = 'COVER' as const

interface TalentImageManagerProps {
  profile: OwnerTalent
  maxGallery?: number
}

/** Profile photo and portfolio management for the caller's own profile. */
export function TalentImageManager({ profile, maxGallery = 10 }: TalentImageManagerProps) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const t = useT()
  const [uploadingKind, setUploadingKind] = useState<ImageKind | null>(null)
  const photoCrop = useCropStep('logo')
  const coverCrop = useCropStep('cover')
  const galleryCrop = useCropStep('gallery')

  const gallery = profile.images.filter((image) => image.kind === 'GALLERY')

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myTalent })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myTalentReadiness })
  }

  const upload = useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: ImageKind }) =>
      ownerTalentApi.uploadImage(file, kind),
    onSuccess: () => {
      toast.success(t('images.uploaded'))
      invalidate()
    },
    onError: (error) =>
      toast.error(t('images.uploadFailed'), error instanceof ApiError ? error.message : undefined),
    onSettled: () => setUploadingKind(null),
  })

  const removeSingle = useMutation({
    mutationFn: (kind: typeof PHOTO_KIND | typeof COVER_KIND) =>
      ownerTalentApi.deleteSingleImage(kind),
    onSuccess: () => {
      toast.success(t('images.deleted'))
      invalidate()
    },
    onError: (error) =>
      toast.error(t('images.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const remove = useMutation({
    mutationFn: (imageId: string) => ownerTalentApi.deleteImage(imageId),
    onSuccess: () => {
      toast.success(t('images.deleted'))
      invalidate()
    },
    onError: (error) =>
      toast.error(t('images.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const reorder = useMutation({
    mutationFn: (imageIds: string[]) => ownerTalentApi.reorderImages(imageIds),
    onSuccess: invalidate,
  })

  const handleFile = async (picked: File | undefined, kind: ImageKind) => {
    if (!picked) return
    if (!ACCEPTED_IMAGE_TYPES.split(',').includes(picked.type)) {
      toast.error(t('images.badType'), t('images.badTypeDescription'))
      return
    }
    // The size is checked on what is sent: a crop is usually much smaller.
    const step = kind === PHOTO_KIND ? photoCrop : kind === COVER_KIND ? coverCrop : galleryCrop
    const file = await step.crop(picked)
    if (!file) return
    if (file.size > MAX_IMAGE_BYTES) {
      toast.error(t('images.tooLarge'), t('images.tooLargeDescription'))
      return
    }
    setUploadingKind(kind)
    upload.mutate({ file, kind })
  }

  const move = (index: number, direction: -1 | 1) => {
    const next = [...gallery]
    const target = index + direction
    const moved = next[index]
    const swapped = next[target]
    if (!moved || !swapped) return
    next[index] = swapped
    next[target] = moved
    reorder.mutate(next.map((image) => image.id))
  }

  return (
    <div className="space-y-8">
      {photoCrop.dialog}
      {coverCrop.dialog}
      {galleryCrop.dialog}
      {/* Both required before review for a service (the owners' ticket, 29
          Oct 2026). Removed by kind: the payload lists only the portfolio. */}
      <div className="grid gap-6 sm:grid-cols-2">
        <SingleImageSlot
          label={t('talentImages.photoTitle')}
          hint={t('talentImages.photoHint')}
          required
          url={profile.photo_url}
          uploading={uploadingKind === PHOTO_KIND}
          onSelect={(file) => void handleFile(file, PHOTO_KIND)}
          onRemove={() => removeSingle.mutate(PHOTO_KIND)}
        />
        <SingleImageSlot
          label={t('images.coverTitle')}
          hint={t('images.coverHint')}
          required={profile.kind === 'SERVICE'}
          url={profile.cover_url ?? null}
          uploading={uploadingKind === COVER_KIND}
          onSelect={(file) => void handleFile(file, COVER_KIND)}
          onRemove={() => removeSingle.mutate(COVER_KIND)}
        />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="font-bold">
            {t('talentImages.portfolioTitle')}
            <span className="ms-2 text-sm font-normal text-ink-500">
              {t('images.galleryCount', { current: gallery.length, max: maxGallery })}
            </span>
          </h3>
          <UploadButton
            label={t('images.addImage')}
            disabled={gallery.length >= maxGallery}
            uploading={uploadingKind === 'GALLERY'}
            onSelect={(file) => void handleFile(file, 'GALLERY')}
          />
        </div>

        {gallery.length === 0 ? (
          <p className="rounded-xl border-2 border-dashed border-ink-100 p-8 text-center text-ink-500">
            {t('talentImages.emptyPortfolio')}
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {gallery.map((image, index) => (
              <li
                key={image.id}
                className="group relative overflow-hidden rounded-xl border border-ink-100 bg-sand-100"
              >
                <img
                  src={image.url}
                  alt={image.caption ?? ''}
                  className="h-32 w-full object-cover"
                />
                <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-ink-900/60 p-1.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => move(index, -1)}
                      disabled={index === 0 || reorder.isPending}
                      className="rounded-md bg-white/90 p-1.5 text-ink-900 disabled:opacity-40"
                      aria-label={t('images.moveBack')}
                    >
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => move(index, 1)}
                      disabled={index === gallery.length - 1 || reorder.isPending}
                      className="rounded-md bg-white/90 p-1.5 text-ink-900 disabled:opacity-40"
                      aria-label={t('images.moveForward')}
                    >
                      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => remove.mutate(image.id)}
                    className="rounded-md bg-clay-600 p-1.5 text-white"
                    aria-label={t('images.deleteImage')}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
