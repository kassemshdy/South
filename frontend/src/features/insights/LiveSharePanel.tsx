import { PartyPopper } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { ShareButton } from '@/components/ui/ShareButton'
import { useT } from '@/i18n'
import { whatsappShareHref } from '@/utils/format'

/**
 * The moment a listing goes live, asked to do something about it.
 *
 * The owner is the cheapest and most credible distribution channel this
 * project has, and the moment they are proudest of the page is the moment to
 * ask them to pass it on. Approval used to just change a badge from orange
 * to green.
 *
 * The URL is the listing's public page, not the dashboard — hence the
 * explicit `url`, since the share sheet would otherwise offer `/dashboard`,
 * which is behind a login and useless to whoever receives it.
 */
export function LiveSharePanel({ name, path }: { name: string; path: string }) {
  const t = useT()
  const url = `${window.location.origin}${path}`
  const message = `${t('dashboard.shareMessage', { name })}\n${url}`

  return (
    <div className="mt-4 rounded-xl border-2 border-olive-200 bg-olive-50 p-3.5">
      <div className="flex gap-2.5">
        <PartyPopper className="mt-0.5 h-5 w-5 shrink-0 text-olive-700" aria-hidden="true" />
        <div className="min-w-0">
          <p className="font-semibold text-olive-900">{t('dashboard.liveTitle')}</p>
          <p className="mt-0.5 text-sm leading-relaxed text-olive-800">
            {t('dashboard.liveDescription')}
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button asChild size="sm">
          <a href={whatsappShareHref(message)} target="_blank" rel="noreferrer noopener">
            {t('dashboard.shareOnWhatsapp')}
          </a>
        </Button>
        <ShareButton title={name} text={message} url={url} variant="outline" />
      </div>
    </div>
  )
}
