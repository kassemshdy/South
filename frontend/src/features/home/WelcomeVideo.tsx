import { Play } from 'lucide-react'
import { useState } from 'react'

import { useT } from '@/i18n'

/**
 * Dr Hossam's introduction to the project.
 *
 * **The video id below is a placeholder** until the real recording exists —
 * swap `VIDEO_ID` and nothing else has to change.
 *
 * Two deliberate choices, both for a visitor on a phone paying for their data:
 *
 * The iframe is not in the page until it is asked for. A YouTube embed pulls
 * several hundred kilobytes and a pile of third-party script on sight, which
 * on a mid-range Android over mobile data is paid for by everybody and watched
 * by a few. Until the tap, this is one image and a button.
 *
 * And the poster is YouTube's own thumbnail rather than a copy checked into
 * the repo, so it cannot fall out of step with the video it stands for.
 */

// TODO: replace with Dr Hossam's introduction once it is recorded.
const VIDEO_ID = 'aqz-KE-bpKQ'

export function WelcomeVideo() {
  const t = useT()
  const [playing, setPlaying] = useState(false)
  const [posterFailed, setPosterFailed] = useState(false)

  return (
    <section className="container-page py-12 sm:py-16" aria-labelledby="welcome-video-heading">
      <div className="mx-auto max-w-3xl text-center">
        <h2 id="welcome-video-heading" className="text-2xl sm:text-3xl">
          {t('home.videoHeading')}
        </h2>
        <p className="mx-auto mt-3 max-w-xl leading-relaxed text-ink-500">
          {t('home.videoSubtitle')}
        </p>
      </div>

      {/* Deep green rather than black behind the poster: a thumbnail that
          fails to load — a blocked network, an unlisted video — then reads as
          an intentional brand panel with a play button on it, not a broken
          image. */}
      <div className="mx-auto mt-8 max-w-3xl overflow-hidden rounded-2xl border-4 border-brand-700 bg-brand-800 shadow-card">
        {/* 16:9 without a plugin, and without the layout shifting when the
            iframe replaces the poster. */}
        <div className="relative aspect-video">
          {playing ? (
            <iframe
              // `autoplay` is only reached by a tap, never on load.
              src={`https://www.youtube-nocookie.com/embed/${VIDEO_ID}?autoplay=1&rel=0`}
              title={t('home.videoHeading')}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="absolute inset-0 h-full w-full"
            />
          ) : (
            <button
              type="button"
              onClick={() => setPlaying(true)}
              className="group absolute inset-0 h-full w-full cursor-pointer focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-wheat-500"
              aria-label={t('home.videoPlayAria')}
            >
              {posterFailed ? null : (
                <img
                  src={`https://i.ytimg.com/vi/${VIDEO_ID}/hqdefault.jpg`}
                  alt=""
                  loading="lazy"
                  onError={() => setPosterFailed(true)}
                  className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
                />
              )}
              <span className="absolute inset-0 flex items-center justify-center">
                <span className="flex h-16 w-16 items-center justify-center rounded-full bg-clay-500 text-white shadow-lift transition-transform group-hover:scale-110 sm:h-20 sm:w-20">
                  {/* Nudged off-centre so the triangle looks centred. */}
                  <Play className="h-7 w-7 translate-x-0.5 sm:h-9 sm:w-9" aria-hidden="true" />
                </span>
              </span>
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
