import { Check, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'

/**
 * Pass this page to someone else.
 *
 * The native share sheet on a phone, the clipboard everywhere else, and a
 * short confirmation either way — the three behaviours the business and talent
 * pages had each written for themselves, in two near-identical copies. A
 * product page had none, which is the odd part: a photo with a price is the
 * most shareable thing on this site and the one thing that could not be
 * shared.
 *
 * `text` is what a recipient reads before deciding whether to open the link,
 * so it is worth more than the site's name — a product passes its own name and
 * price.
 */
export function ShareButton({
  title,
  text,
  url,
  block = false,
  variant = 'outline',
  className,
}: {
  title: string
  text?: string | undefined
  /**
   * What to share. Defaults to the page the button is on, which is right on
   * a public profile and wrong on the dashboard — sharing a listing from
   * there must pass the listing's own public URL, not `/dashboard`.
   */
  url?: string | undefined
  block?: boolean
  variant?: 'outline' | 'ghost'
  className?: string
}) {
  const t = useT()
  const [copied, setCopied] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  // The confirmation resets on a timer; if the page unmounts first, setting
  // state on a gone component is a warning nobody needs.
  useEffect(() => () => window.clearTimeout(timer.current), [])

  const share = async () => {
    const target = url ?? window.location.href

    if (navigator.share) {
      try {
        await navigator.share({ title, text: text ?? '', url: target })
        return
      } catch {
        /* the sheet was dismissed — fall through and copy instead */
      }
    }

    try {
      await navigator.clipboard.writeText(target)
      setCopied(true)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setCopied(false), 2500)
    } catch {
      /* no clipboard either: the URL is in the address bar regardless */
    }
  }

  return (
    <Button
      type="button"
      variant={variant}
      block={block}
      onClick={() => void share()}
      className={className}
    >
      {copied ? (
        <>
          <Check className="h-4 w-4" aria-hidden="true" />
          {t('business.linkCopied')}
        </>
      ) : (
        <>
          <Share2 className="h-4 w-4" aria-hidden="true" />
          {t('business.share')}
        </>
      )}
    </Button>
  )
}
