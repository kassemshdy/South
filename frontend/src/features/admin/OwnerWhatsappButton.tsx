import { MessageCircle } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import { whatsappHref } from '@/utils/format'

/**
 * A chat with the account holder, from the reviewer's own WhatsApp: the way
 * to ask a question about an application, or about a listing later, without
 * copying the number by hand. The sign-in number, because it is the one the
 * applicant typed as theirs; nothing is pre-written, since the reason to
 * write varies every time.
 */
export function OwnerWhatsappButton({ phone }: { phone: string | null }) {
  const t = useT()
  const href = whatsappHref(phone)
  if (!href) return null
  return (
    <Button asChild variant="outline" size="sm">
      <a href={href} target="_blank" rel="noopener noreferrer">
        <MessageCircle className="h-4 w-4" aria-hidden="true" />
        {t('business.whatsappCta')}
      </a>
    </Button>
  )
}
