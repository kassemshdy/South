import { YouTubePlayer } from '@/components/ui/YouTubePlayer'
import { useUploadedCover } from '@/hooks/usePageCover'
import { usePageText } from '@/hooks/usePageText'
import { useSiteSettings } from '@/hooks/useSiteSettings'
import { useT } from '@/i18n'

/**
 * The "how to register" video on /offer, above the steps.
 *
 * Everything in it is the administrator's: the video is a site setting (a
 * YouTube link, kept as its id), the heading and the text under it are the
 * `offer_video` block on the pages screen, and its preview image is uploaded
 * beside the link (`offer_video` in page covers). Unlike the homepage there is no
 * recording to fall back to, so with no video set the section is absent.
 */
export function OfferVideo() {
  const t = useT()
  const { settings } = useSiteSettings()
  const text = usePageText('offer_video')
  const poster = useUploadedCover('offer_video')
  const videoId = settings?.offer_video
  if (!videoId) return null

  const title = text.title ?? t('offerPage.videoTitle')
  return (
    <section>
      <h2 className="text-lg font-bold text-ink-900">{title}</h2>
      {text.summary ? (
        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-ink-500">
          {text.summary}
        </p>
      ) : null}
      <div className="mt-5">
        <YouTubePlayer
          videoId={videoId}
          poster={poster}
          title={title}
          playLabel={t('offerPage.videoPlayAria')}
        />
      </div>
    </section>
  )
}
