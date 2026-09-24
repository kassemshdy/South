import type { ReactNode } from 'react'

/**
 * The photograph at the top of an inner page, with the page's heading on it.
 *
 * The CEO asked for the place itself on the pages people browse, not only at
 * the foot of the homepage: an aerial of the coast behind the directory
 * heading says "this is the South" before a single card has loaded.
 *
 * One image for every inner page, set here, so replacing it is one file and
 * one line. The photograph fills the band with `object-cover` rather than
 * setting its height: a 16:9 image at phone width is a letterbox strip, and
 * the band is sized by its words instead. The deep green behind it is what
 * shows while the image loads, so the heading is never white on white.
 */
export const PAGE_BANNER_IMAGE = '/south-hills.jpg'

export function PageBanner({
  title,
  subtitle,
  imageAlt,
  children,
}: {
  title: string
  subtitle?: ReactNode
  /** Empty when the photograph is decoration and the heading says it all. */
  imageAlt?: string
  /** Rendered above the heading — a way back, for instance. */
  children?: ReactNode
}) {
  return (
    <div className="relative isolate overflow-hidden border-b-4 border-wheat-500 bg-brand-700">
      <img
        src={PAGE_BANNER_IMAGE}
        alt={imageAlt ?? ''}
        width={1200}
        height={630}
        decoding="async"
        className="absolute inset-0 -z-10 h-full w-full object-cover"
      />
      {/* ink-900, like the homepage scrim. One even wash rather than a
          gradient toward the words: which side they sit on flips with the
          language, and on a phone they cover most of the band anyway. */}
      <div className="absolute inset-0 -z-10 bg-ink-900/55" aria-hidden="true" />
      <div className="container-page py-12 sm:py-16">
        {children}
        <h1 className="max-w-2xl text-balance text-3xl font-bold text-white drop-shadow-sm sm:text-4xl">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-3 max-w-2xl text-balance leading-relaxed text-white/90 sm:text-lg">
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  )
}
