import { useState, type ImgHTMLAttributes } from 'react'

/**
 * A photo drawn small, from its card-sized copy.
 *
 * Cards used to download the full upload -- a 1600px cover, around 330 KB,
 * for a strip about 380px wide -- so one page of results on a phone was
 * several megabytes of pictures nobody could see at that size. The server
 * now keeps a small copy beside each photo and names it `*_thumb_url`.
 *
 * Falls back to the full image when there is no small copy, or when it fails
 * to load (a photo uploaded before thumbnails existed, on a deploy where the
 * backfill has not reached it yet). Either way the card shows a picture.
 */
export function CardImage({
  src,
  thumbSrc,
  ...props
}: Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> & {
  src: string
  thumbSrc?: string | null
}) {
  const [failed, setFailed] = useState(false)
  const current = thumbSrc && !failed ? thumbSrc : src

  return (
    <img
      {...props}
      src={current}
      loading={props.loading ?? 'lazy'}
      decoding="async"
      onError={(event) => {
        if (current !== src) setFailed(true)
        props.onError?.(event)
      }}
    />
  )
}
