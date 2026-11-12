import { ExternalLink, Play } from 'lucide-react'
import { useState } from 'react'

import { useT, type TranslationKey } from '@/i18n'
import type { TalentVideo } from '@/types/api'

const PLATFORM_KEYS: Record<TalentVideo['platform'], TranslationKey> = {
  YOUTUBE: 'platform.YOUTUBE',
  INSTAGRAM: 'platform.INSTAGRAM',
  TIKTOK: 'platform.TIKTOK',
  FACEBOOK: 'platform.FACEBOOK',
}

/**
 * Videos of a services provider's work (the owners' review, 12 Nov 2026).
 * Each loads its platform's player only when tapped, as the introduction
 * video does: no third-party request is made for a visitor who only reads.
 * The addresses are the server's, rebuilt on each platform's own host.
 */
export function WorkVideos({ videos }: { videos: TalentVideo[] }) {
  const t = useT()
  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {videos.map((video) => (
        <li key={video.embed_url}>
          <WorkVideoTile video={video} platform={t(PLATFORM_KEYS[video.platform])} />
        </li>
      ))}
    </ul>
  )
}

function WorkVideoTile({ video, platform }: { video: TalentVideo; platform: string }) {
  const t = useT()
  const [playing, setPlaying] = useState(false)
  // Reels and TikToks are tall; YouTube and Facebook videos are wide.
  const tall = video.platform === 'INSTAGRAM' || video.platform === 'TIKTOK'
  return (
    <div className="overflow-hidden rounded-2xl border border-ink-100 bg-white">
      <div className={tall ? 'aspect-[9/16] max-h-[36rem] w-full' : 'aspect-video w-full'}>
        {playing ? (
          <iframe
            src={video.embed_url}
            title={platform}
            className="h-full w-full"
            loading="lazy"
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            className="flex h-full w-full flex-col items-center justify-center gap-2 bg-ink-900 text-white"
            aria-label={`${t('video.playAria')} (${platform})`}
          >
            <Play className="h-10 w-10" aria-hidden="true" />
            <span className="text-sm font-semibold">{platform}</span>
          </button>
        )}
      </div>
      <a
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-2 text-sm text-brand-700 hover:underline"
      >
        <ExternalLink className="h-4 w-4" aria-hidden="true" />
        {t('workVideos.open')}
      </a>
    </div>
  )
}
