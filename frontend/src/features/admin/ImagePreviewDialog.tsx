import { Download } from 'lucide-react'

import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useT } from '@/i18n'

import type { PreviewImage } from './openPrivateFile'

/**
 * A listing's public image in a popup on the review page, rather than a new
 * tab (the owners' request, 3 Nov 2026); an ID scan opened from a blob too,
 * with a button to save it (14 Nov 2026: see it first, download if needed).
 */
export function ImagePreviewDialog({
  image,
  onClose,
}: {
  image: PreviewImage | null
  onClose: () => void
}) {
  const t = useT()
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
          {image.filename ? (
            <a
              href={image.url}
              download={image.filename}
              className="mx-auto mt-3 inline-flex min-h-9 items-center gap-1.5 rounded-xl border border-ink-200 px-3 text-sm font-semibold text-ink-700 hover:bg-sand-100"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              {t('admin.exportDownload')}
            </a>
          ) : null}
        </DialogContent>
      ) : null}
    </Dialog>
  )
}
