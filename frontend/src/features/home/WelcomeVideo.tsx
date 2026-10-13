import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useT } from '@/i18n'

/**
 * The introduction video on the homepage.
 *
 * The framed player and nothing else — no heading, no width, no section. It
 * sits in the homepage hero beside the copy, so the surrounding section owns
 * the layout and the caption; this owns only which recording plays and which
 * poster stands in for it. The frame, the tap and the
 * nothing-loads-until-asked rule live in `YouTubePlayer`, shared now with the
 * introduction video on a business or talent profile.
 *
 * A poster is our own file rather than `i.ytimg.com/vi/<id>/…`: the
 * recording lives on someone else's channel, so its YouTube thumbnail carries
 * that channel's watermark and none of our branding. Each poster is keyed by
 * the recording it was made for, so a different recording gets the brand
 * panel rather than a face that is not in it.
 *
 * A poster keeps its subject on the reading-end side and its type clear of
 * the centre, because the play button is drawn on top of the middle of the
 * frame. A new one means honouring that or moving the button.
 */

/** The recording the owners chose (round 3); an administrator can replace it. */
const VIDEO_ID = 'cxylydvdiNE'

/** Posters we have, by the recording each was made for. */
const POSTERS: Record<string, string> = {
  // Dr Hossam Matar's earlier introduction.
  '3Np8hKhrbB4': '/welcome-hossam-matar.webp',
  // The owners' new introduction is Dr Hossam too, so it takes his poster.
  cxylydvdiNE: '/welcome-hossam-matar.webp',
}

export function WelcomeVideoPlayer() {
  const t = useT()
  const { settings } = useSiteSettings()
  const videoId = settings?.home_video ?? VIDEO_ID

  return (
    <YouTubePlayer
      videoId={videoId}
      poster={POSTERS[videoId] ?? null}
      title={t('home.videoHeading')}
      playLabel={t('home.videoPlayAria')}
    />
  )
}
