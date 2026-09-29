/**
 * Re-encode a photograph in the browser so it fits under the upload limit.
 *
 * A photo straight off a camera or out of a designer's export is routinely
 * 8-20 MB, over the API's 5 MB limit, while the server keeps nothing wider
 * than 1600px of it anyway. Shrinking here means any ordinary photo just
 * works, without raising a limit that exists to protect the server.
 *
 * Decoding goes through an `<img>` rather than `createImageBitmap` so a
 * phone photo's EXIF rotation is honoured the same way in every browser.
 * The result is a JPEG on white: a banner has no use for transparency, and
 * a transparent PNG drawn onto a JPEG would otherwise come out black.
 *
 * A file that is already small enough is returned untouched.
 */
export async function shrinkImage(
  file: File,
  { maxBytes, maxSide = 2400, quality = 0.85 }: { maxBytes: number; maxSide?: number; quality?: number },
): Promise<File> {
  if (file.size <= maxBytes) return file

  const url = URL.createObjectURL(file)
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image()
      element.onload = () => resolve(element)
      element.onerror = () => reject(new Error('decode failed'))
      element.src = url
    })

    const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight))
    const width = Math.round(image.naturalWidth * scale)
    const height = Math.round(image.naturalHeight * scale)

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) return file
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, width, height)
    context.drawImage(image, 0, 0, width, height)

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', quality),
    )
    if (!blob) return file
    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], name, { type: 'image/jpeg' })
  } finally {
    URL.revokeObjectURL(url)
  }
}
