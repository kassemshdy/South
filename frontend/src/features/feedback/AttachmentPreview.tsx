import { FileText, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'

import { apiDownload } from '@/services/api/client'
import { feedbackApi } from '@/services/api/endpoints'
import type { FeedbackAttachment } from '@/types/api'

/**
 * A feedback attachment's bytes are admin-gated, unlike a business photo —
 * see the model docstring in `app/models/feedback.py` — so this fetches them
 * with the caller's bearer token via `apiDownload` and renders a local blob
 * URL, rather than pointing an `<img>` at a public path.
 */
export function AttachmentPreview({
  ticketId,
  attachment,
}: {
  ticketId: string
  attachment: FeedbackAttachment
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    apiDownload(feedbackApi.attachmentUrl(ticketId, attachment.id))
      .then(({ blob }) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [ticketId, attachment.id])

  const isImage = attachment.content_type.startsWith('image/')

  if (failed) {
    return (
      <div className="flex h-24 items-center justify-center rounded-lg bg-sand-100 text-xs text-ink-300">
        —
      </div>
    )
  }

  if (!url) {
    return (
      <div className="flex h-24 items-center justify-center rounded-lg bg-sand-100">
        <Loader2 className="h-5 w-5 animate-spin text-ink-300" aria-hidden="true" />
      </div>
    )
  }

  if (isImage) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className="block">
        <img
          src={url}
          alt={attachment.original_filename ?? ''}
          className="h-24 w-full rounded-lg object-cover"
        />
      </a>
    )
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex h-24 flex-col items-center justify-center gap-1 rounded-lg bg-sand-100 p-2 text-center text-xs text-ink-700 hover:bg-sand-200"
    >
      <FileText className="h-6 w-6" aria-hidden="true" />
      <span className="line-clamp-2 break-all">{attachment.original_filename ?? 'document'}</span>
    </a>
  )
}
