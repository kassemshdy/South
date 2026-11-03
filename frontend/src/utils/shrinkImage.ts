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

const SHRINKABLE = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp'])
/** Under the API's 5 MB image limit, with room for the multipart envelope. */
const UPLOAD_TARGET_BYTES = 4.5 * 1024 * 1024

/**
 * The same form with every photo in it brought under the limit, for the one
 * place every upload passes (`apiRequest`). Product photos went straight to
 * the API at whatever size the phone produced, and owners were refused for
 * photos over 5 MB -- three times in one morning. A PDF, or a photo the
 * browser cannot decode, is sent exactly as chosen and the server decides.
 */
export async function shrinkImagesIn(form: FormData): Promise<FormData> {
  const shrunk = new FormData()
  for (const [key, value] of form.entries()) {
    if (value instanceof File) {
      const copy = await inMemory(value)
      const file = SHRINKABLE.has(copy.type.toLowerCase())
        ? await shrinkImage(copy, { maxBytes: UPLOAD_TARGET_BYTES }).catch(() => copy)
        : copy
      shrunk.append(key, file, file.name)
    } else {
      shrunk.append(key, value)
    }
  }
  return shrunk
}

/** A picked file whose bytes the browser could no longer read. */
export class UnreadableFileError extends Error {
  constructor() {
    super('unreadable file')
    this.name = 'UnreadableFileError'
  }
}

/**
 * The same file, held in memory.
 *
 * A photo picked on Android (above all from Google Photos or another cloud
 * gallery) is a reference to the phone's storage, and the browser can lose
 * the right to read it before the upload starts: fetch then fails at once
 * and the owner was told to check their internet (the owners' ticket, 30 Oct
 * 2026). Reading the bytes as soon as the photo is picked, and again before
 * sending, keeps a copy the browser can always send, and turns the failure
 * into a message that says what actually happened.
 */
export async function inMemory(file: File): Promise<File> {
  try {
    const bytes = await file.arrayBuffer()
    return new File([bytes], file.name, { type: file.type, lastModified: file.lastModified })
  } catch {
    throw new UnreadableFileError()
  }
}
