import { Facebook, Globe, Instagram, Link2, MessageCircle, Music2, Youtube } from 'lucide-react'

import { Card, CardBody } from '@/components/ui/Card'
import { useT } from '@/i18n'
import type { SocialLink, SocialPlatform } from '@/types/api'
import { PLATFORM_KEYS } from '@/utils/format'

const PLATFORM_ICONS: Record<SocialPlatform, typeof Instagram> = {
  INSTAGRAM: Instagram,
  FACEBOOK: Facebook,
  TIKTOK: Music2,
  YOUTUBE: Youtube,
  WHATSAPP: MessageCircle,
  WEBSITE: Globe,
}

/**
 * A profile's social accounts, as a card of links -- nothing at all when
 * there are none, since every one of them is optional.
 */
export function FollowLinks({ links }: { links: SocialLink[] }) {
  const t = useT()
  if (links.length === 0) return null
  return (
    <Card>
      <CardBody className="space-y-3">
        <h2 className="text-lg font-bold">{t('business.followHeading')}</h2>
        {links.map((link) => {
          const Icon = PLATFORM_ICONS[link.platform] ?? Link2
          return (
            <a
              key={link.platform}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-lg p-2 text-ink-700 transition-colors hover:bg-sand-100 hover:text-brand-700"
            >
              <Icon className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
              {t(PLATFORM_KEYS[link.platform])}
            </a>
          )
        })}
      </CardBody>
    </Card>
  )
}
