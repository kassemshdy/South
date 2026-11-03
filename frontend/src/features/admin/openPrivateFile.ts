/** An image to show in `ImagePreviewDialog`; `revoke` frees a blob URL on close. */
export type PreviewImage = { title: string; url: string; revoke?: boolean }

/**
 * Opens a downloaded private file the way the owners asked (3 Nov 2026):
 * an image in a popup, a PDF in a new tab, anything else as a download.
 */
export function openPrivateFile(
  { blob, filename }: { blob: Blob; filename: string | null },
  showImage: (image: PreviewImage) => void,
  title: string,
): void {
  const url = URL.createObjectURL(blob)
  if (blob.type.startsWith('image/')) {
    showImage({ title, url, revoke: true })
    return
  }
  if (blob.type === 'application/pdf' && window.open(url, '_blank')) {
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    return
  }
  const link = document.createElement('a')
  link.href = url
  link.download = filename ?? 'document'
  link.click()
  URL.revokeObjectURL(url)
}
