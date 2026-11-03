import { useState, type ReactNode } from 'react'

import { ImageCropDialog } from '@/features/images/ImageCropDialog'

interface CropRequest {
  file: File
  aspect: number
  ratios?: number[]
  done: (file: File) => void
}

/**
 * Put the crop step in front of any upload: `crop(file, shape, upload)`
 * opens the dialog, and `upload` receives the cropped file. Render
 * `dialog` once anywhere in the component.
 */
export function useCropper(): {
  crop: (file: File, shape: { aspect: number; ratios?: number[] }, done: (file: File) => void) => void
  dialog: ReactNode
} {
  const [request, setRequest] = useState<CropRequest | null>(null)
  return {
    crop: (file, shape, done) => setRequest({ file, ...shape, done }),
    dialog: (
      <ImageCropDialog
        file={request?.file ?? null}
        aspect={request?.aspect ?? 1}
        {...(request?.ratios ? { ratios: request.ratios } : {})}
        onCancel={() => setRequest(null)}
        onCropped={(file) => {
          request?.done(file)
          setRequest(null)
        }}
      />
    ),
  }
}
