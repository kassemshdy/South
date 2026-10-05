import type { UseFormRegisterReturn } from 'react-hook-form'

import { useT } from '@/i18n'

/**
 * Whether the numbers just above are shown to visitors.
 *
 * The owners asked that everyone listing give a number and choose whether
 * the public sees it. Unticked, the number still reaches the team and stays
 * on the owner's dashboard; a visitor reaches the owner through a message on
 * the site instead, and is not offered WhatsApp or a call.
 */
export function PhonePublicToggle({ registration }: { registration: UseFormRegisterReturn }) {
  const t = useT()
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-ink-100 bg-sand-50/60 p-3">
      <input type="checkbox" {...registration} className="mt-1 h-4 w-4 accent-brand-700" />
      <span>
        <span className="font-semibold text-ink-900">{t('form.phonePublicLabel')}</span>
        <span className="mt-0.5 block text-sm text-ink-500">{t('form.phonePublicHint')}</span>
      </span>
    </label>
  )
}
