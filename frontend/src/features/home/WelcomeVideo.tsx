import { Play } from 'lucide-react'
import { useState } from 'react'

import { useT } from '@/i18n'

/**
 * Dr Hossam Matar's introduction to the project.
 *
 * The framed player and nothing else — no heading, no width, no section. It
 * sits in the homepage hero beside the copy, so the surrounding section owns
 * the layout and the caption; this owns only the 16:9 frame and the tap.
 *
 * Two deliberate choices, both for a visitor on a phone paying for their data:
 *
 * The iframe is not in the page until it is asked for. A YouTube embed pulls
 * several hundred kilobytes and a pile of third-party script on sight, which
 * on a mid-range Android over mobile data is paid for by everybody and watched
 * by a few. Until the tap, this is one image and a button.
 *
 * And the poster is our own file rather than `i.ytimg.com/vi/<id>/…`. Three
 * reasons, in order of weight: the recording lives on someone else's channel,
 * so its YouTube thumbnail carries that channel's watermark and none of our
 * branding; a same-origin image means the homepage makes no third-party
 * request at all before anybody taps; and the poster then loads from the same
 * cache as the rest of the site. The cost is that the two can drift apart, so
 * `POSTER` is named after the speaker it shows — a new recording by someone
 * else makes the mismatch obvious rather than quiet.
 *
 * The poster keeps its subject on the reading-end side and its type clear of
 * the centre, because the play button below is drawn on top of the middle of
 * the frame. Replacing the image means honouring that or moving the button.
 */

const VIDEO_ID = '3Np8hKhrbB4'
const POSTER = '/welcome-hossam-matar.jpg'

export function WelcomeVideoPlayer() {
  const t = useT()
  const [playing, setPlaying] = useState(false)
  const [posterFailed, setPosterFailed] = useState(false)

  return (
    /* Deep green rather than black behind the poster: a thumbnail that fails
       to load — a bad deploy, a blocked request — then reads as an intentional
       brand panel with a play button on it, not a broken image. */
    <div className="overflow-hidden rounded-2xl border-4 border-brand-700 bg-brand-800 shadow-card">
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
                src={POSTER}
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
  )
}
