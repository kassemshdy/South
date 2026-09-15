import { Play } from 'lucide-react'
import { useState } from 'react'

/**
 * A framed YouTube video that loads nothing until it is asked to.
 *
 * Extracted from the homepage welcome video once listings gained an
 * introduction video of their own, so there is one implementation of the two
 * decisions that matter here rather than three copies of them:
 *
 * The iframe is not in the page until the tap. A YouTube embed pulls several
 * hundred kilobytes and a pile of third-party script on sight, which on a
 * mid-range Android over mobile data is paid for by everybody and watched by
 * a few. Until then this is one image and a button.
 *
 * And the poster is ours, never `i.ytimg.com/vi/<id>/…`. A listing passes its
 * own cover photo, which is same-origin, already in the visitor's cache from
 * the page around it, and carries no other channel's watermark — so a profile
 * makes no third-party request at all before anybody asks to watch. When
 * there is no poster to pass, or it fails to load, the brand panel below is
 * what remains: deliberately a panel with a play button on it rather than a
 * broken image.
 *
 * `videoId` is an id, not a URL, and the embed address is composed here. The
 * server stores the id precisely so that no string an owner typed is ever
 * handed to a browser — see `app.core.urls.youtube_video_id`.
 */

interface YouTubePlayerProps {
  /** An eleven-character YouTube id, validated server-side. */
  videoId: string
  /** Same-origin poster. Omit to show the brand panel. */
  poster?: string | null
  /** Accessible title for the iframe, and the alt-free poster's context. */
  title: string
  /** Label for the play button, read out before the tap. */
  playLabel: string
}

export function YouTubePlayer({ videoId, poster, title, playLabel }: YouTubePlayerProps) {
  const [playing, setPlaying] = useState(false)
  const [posterFailed, setPosterFailed] = useState(false)

  return (
    <div className="overflow-hidden rounded-2xl border-4 border-brand-700 bg-brand-800 shadow-card">
      {/* 16:9 without a plugin, and without the layout shifting when the
          iframe replaces the poster. */}
      <div className="relative aspect-video">
        {playing ? (
          <iframe
            // `autoplay` is only ever reached by a tap, never on load.
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`}
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="absolute inset-0 h-full w-full"
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            className="group absolute inset-0 h-full w-full cursor-pointer focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-wheat-500"
            aria-label={playLabel}
          >
            {poster && !posterFailed ? (
              <img
                src={poster}
                alt=""
                loading="lazy"
                onError={() => setPosterFailed(true)}
                className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
              />
            ) : null}
            <span className="absolute inset-0 flex items-center justify-center">
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-800 text-white shadow-lift transition-transform group-hover:scale-110 sm:h-20 sm:w-20">
                {/* Nudged off-centre so the triangle looks centred. */}
                <Play className="h-7 w-7 translate-x-0.5 sm:h-9 sm:w-9" aria-hidden="true" />
              </span>
            </span>
          </button>
        )}
      </div>
    </div>
  )
}
