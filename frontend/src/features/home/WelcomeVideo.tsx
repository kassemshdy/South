import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { useT } from '@/i18n'

/**
 * Dr Hossam Matar's introduction to the project.
 *
 * The framed player and nothing else — no heading, no width, no section. It
 * sits in the homepage hero beside the copy, so the surrounding section owns
 * the layout and the caption; this owns only which recording plays and which
 * poster stands in for it. The frame, the tap and the
 * nothing-loads-until-asked rule live in `YouTubePlayer`, shared now with the
 * introduction video on a business or talent profile.
 *
 * The poster is our own file rather than `i.ytimg.com/vi/<id>/…`: the
 * recording lives on someone else's channel, so its YouTube thumbnail carries
 * that channel's watermark and none of our branding. The cost is that the two
 * can drift apart, so `POSTER` is named after the speaker it shows — a new
 * recording by someone else makes the mismatch obvious rather than quiet.
 *
 * The poster keeps its subject on the reading-end side and its type clear of
 * the centre, because the play button is drawn on top of the middle of the
 * frame. Replacing the image means honouring that or moving the button.
 */

const VIDEO_ID = '3Np8hKhrbB4'
const POSTER = '/welcome-hossam-matar.webp'

export function WelcomeVideoPlayer() {
  const t = useT()

  return (
    <YouTubePlayer
      videoId={VIDEO_ID}
      poster={POSTER}
      title={t('home.videoHeading')}
      playLabel={t('home.videoPlayAria')}
    />
  )
}
