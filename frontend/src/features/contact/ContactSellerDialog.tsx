import { MessageCircle, Phone } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useT } from '@/i18n'

/**
 * Offered straight after a request is stored: reach the seller now, by
 * WhatsApp or a call, rather than waiting for them to find it.
 *
 * The request is already saved when this opens, so closing it costs nothing —
 * it is a shortcut, never a step. It renders nothing when the seller chose to
 * keep their number private: the public payload carries no number then, and
 * the stored request is the only way to reach them, which is what they asked
 * for.
 */
export function ContactSellerDialog({
  open,
  onOpenChange,
  whatsapp,
  phone,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** A ready `wa.me` link (`whatsappHref`), or null. */
  whatsapp: string | null
  /** A ready `tel:` link (`telHref`), or null. */
  phone: string | null
}) {
  const t = useT()
  if (!whatsapp && !phone) return null
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t('contactSeller.title')}>
        <div className="flex flex-col gap-2.5">
          {whatsapp ? (
            <Button asChild size="lg" block>
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-5 w-5" aria-hidden="true" />
                {t('business.whatsappCta')}
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button asChild size="lg" variant="outline" block>
              <a href={phone}>
                <Phone className="h-5 w-5" aria-hidden="true" />
                {t('business.callCta')}
              </a>
            </Button>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
