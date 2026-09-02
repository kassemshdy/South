import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, ImagePlus, Loader2, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { ApiError } from '@/services/api/client'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ImageKind, OwnerBusiness } from '@/types/api'

const MAX_BYTES = 5 * 1024 * 1024
const ACCEPTED = 'image/jpeg,image/png,image/webp'

interface ImageManagerProps {
  business: OwnerBusiness
  maxGallery?: number
}

/**
 * Logo, cover and gallery management.
 *
 * Files are checked for type and size before upload so the user gets an
 * immediate Arabic message instead of waiting for a round trip; the server
 * validates again by actually decoding the image.
 */
export function ImageManager({ business, maxGallery = 10 }: ImageManagerProps) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [uploadingKind, setUploadingKind] = useState<ImageKind | null>(null)

  const gallery = business.images.filter((image) => image.kind === 'GALLERY')

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(business.id) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const upload = useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: ImageKind }) =>
      ownerApi.uploadImage(business.id, file, kind),
    onSuccess: () => {
      toast.success('تم رفع الصورة')
      invalidate()
    },
    onError: (error) =>
      toast.error('تعذر رفع الصورة', error instanceof ApiError ? error.message : undefined),
    onSettled: () => setUploadingKind(null),
  })

  const remove = useMutation({
    mutationFn: (imageId: string) => ownerApi.deleteImage(business.id, imageId),
    onSuccess: () => {
      toast.success('تم حذف الصورة')
      invalidate()
    },
    onError: (error) =>
      toast.error('تعذر حذف الصورة', error instanceof ApiError ? error.message : undefined),
  })

  const reorder = useMutation({
    mutationFn: (imageIds: string[]) => ownerApi.reorderImages(business.id, imageIds),
    onSuccess: invalidate,
  })

  const handleFile = (file: File | undefined, kind: ImageKind) => {
    if (!file) return
    if (!ACCEPTED.split(',').includes(file.type)) {
      toast.error('نوع ملف غير مدعوم', 'يُسمح بصور JPG أو PNG أو WEBP فقط.')
      return
    }
    if (file.size > MAX_BYTES) {
      toast.error('حجم الصورة كبير', 'الحد الأقصى 5 ميغابايت للصورة الواحدة.')
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
      <div className="grid gap-6 sm:grid-cols-2">
        <SingleImageSlot
          label="شعار النشاط"
          hint="مربّع الشكل، يظهر في البطاقة وأعلى الصفحة."
          required
          url={business.logo_url}
          uploading={uploadingKind === 'LOGO'}
          onSelect={(file) => handleFile(file, 'LOGO')}
          onRemove={() => {
            const logo = business.images.find((image) => image.kind === 'LOGO')
            if (logo) remove.mutate(logo.id)
          }}
        />
        <SingleImageSlot
          label="صورة الغلاف"
          hint="عريضة، تظهر أعلى صفحة نشاطك."
          url={business.cover_url}
          uploading={uploadingKind === 'COVER'}
          onSelect={(file) => handleFile(file, 'COVER')}
          onRemove={() => {
            const cover = business.images.find((image) => image.kind === 'COVER')
            if (cover) remove.mutate(cover.id)
          }}
        />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="font-bold">
            معرض الصور
            <span className="ms-2 text-sm font-normal text-ink-500">
              {gallery.length} من {maxGallery}
            </span>
          </h3>
          <UploadButton
            label="إضافة صورة"
            disabled={gallery.length >= maxGallery}
            uploading={uploadingKind === 'GALLERY'}
            onSelect={(file) => handleFile(file, 'GALLERY')}
          />
        </div>

        {gallery.length === 0 ? (
          <p className="rounded-xl border-2 border-dashed border-ink-100 p-8 text-center text-ink-500">
            لم تُضف صوراً بعد. الصور تزيد ثقة الزوار بنشاطك.
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {gallery.map((image, index) => (
              <li key={image.id} className="group relative overflow-hidden rounded-xl border border-ink-100 bg-sand-100">
                <img src={image.url} alt={image.caption ?? ''} className="h-32 w-full object-cover" />
                <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-ink-900/60 p-1.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => move(index, -1)}
                      disabled={index === 0 || reorder.isPending}
                      className="rounded-md bg-white/90 p-1.5 text-ink-900 disabled:opacity-40"
                      aria-label="تحريك للخلف"
                    >
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => move(index, 1)}
                      disabled={index === gallery.length - 1 || reorder.isPending}
                      className="rounded-md bg-white/90 p-1.5 text-ink-900 disabled:opacity-40"
                      aria-label="تحريك للأمام"
                    >
                      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => remove.mutate(image.id)}
                    className="rounded-md bg-clay-600 p-1.5 text-white"
                    aria-label="حذف الصورة"
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

function SingleImageSlot({
  label,
  hint,
  url,
  required,
  uploading,
  onSelect,
  onRemove,
}: {
  label: string
  hint: string
  url: string | null
  required?: boolean
  uploading: boolean
  onSelect: (file: File | undefined) => void
  onRemove: () => void
}) {
  return (
    <div>
      <h3 className="font-bold">
        {label}
        {required ? <span className="ms-1 text-clay-500">*</span> : null}
      </h3>
      <p className="mb-3 text-sm text-ink-500">{hint}</p>

      <div className="flex items-center gap-4">
        <div className="h-24 w-24 shrink-0 overflow-hidden rounded-xl border-2 border-dashed border-ink-100 bg-sand-50">
          {url ? (
            <img src={url} alt={`معاينة ${label}`} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-ink-300">
              <ImagePlus className="h-7 w-7" aria-hidden="true" />
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <UploadButton label={url ? 'استبدال' : 'رفع صورة'} uploading={uploading} onSelect={onSelect} />
          {url ? (
            <Button type="button" variant="ghost" size="sm" onClick={onRemove}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              حذف
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function UploadButton({
  label,
  uploading,
  disabled,
  onSelect,
}: {
  label: string
  uploading: boolean
  disabled?: boolean
  onSelect: (file: File | undefined) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="sr-only"
        onChange={(event) => {
          onSelect(event.target.files?.[0])
          // Reset so selecting the same file twice still fires a change event.
          event.target.value = ''
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            جارٍ الرفع…
          </>
        ) : (
          <>
            <ImagePlus className="h-4 w-4" aria-hidden="true" />
            {label}
          </>
        )}
      </Button>
    </>
  )
}
