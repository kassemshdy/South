import { Dialog, DialogContent } from '@/components/ui/Dialog'

import type { PreviewImage } from './openPrivateFile'

/**
 * A listing's public image in a popup on the review page, rather than a new
 * tab (the owners' request, 3 Nov 2026); an ID scan opened from a blob too.
 */
export function ImagePreviewDialog({
  image,
  onClose,
}: {
  image: PreviewImage | null
  onClose: () => void
}) {
  const close = () => {
    if (image?.revoke) URL.revokeObjectURL(image.url)
    onClose()
  }
  return (
    <Dialog open={image !== null} onOpenChange={(open) => (open ? null : close())}>
      {image ? (
        <DialogContent title={image.title} className="max-w-3xl">
          <img
            src={image.url}
            alt=""
            className="mx-auto max-h-[70dvh] w-auto rounded-xl object-contain"
          />
        </DialogContent>
      ) : null}
    </Dialog>
  )
}
