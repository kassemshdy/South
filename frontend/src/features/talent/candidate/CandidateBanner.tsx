import type { ReactNode } from 'react'

import { usePageCover } from '@/hooks/usePageCover'

/**
 * The candidate directory's photo band: the same cover as `PageBanner`,
 * held to about 200px on a desktop and 140px on a phone so the results show
 * sooner (the owners' ticket, 31 Oct 2026), with a line for employers.
 */
export function CandidateBanner({
  title,
  count,
  line,
}: {
  title: string
  count: ReactNode
  line: string
}) {
  const cover = usePageCover('jobs')
  return (
    <div className="relative isolate h-[140px] overflow-hidden border-b-4 border-wheat-500 bg-brand-700 sm:h-[200px]">
      <img
        src={cover.src}
        alt=""
        width={1200}
        height={630}
        decoding="async"
        className="absolute inset-0 -z-10 h-full w-full object-cover"
      />
      <div className="absolute inset-0 -z-10 bg-ink-900/55" aria-hidden="true" />
      <div className="container-page flex h-full flex-col justify-center gap-1">
        <h1 className="text-2xl font-bold text-white drop-shadow-sm sm:text-3xl">{title}</h1>
        <p className="text-sm text-white/90 sm:text-base">
          <span className="font-semibold">{count}</span>
          <span className="hidden sm:inline"> · {line}</span>
        </p>
        <p className="text-sm text-white/90 sm:hidden">{line}</p>
      </div>
    </div>
  )
}
