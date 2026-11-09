import { useMutation, useQuery } from '@tanstack/react-query'
import { MessageSquareText } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * Text a shop owner's account number through bestsmsbulk.com (the owners'
 * request, 9 Nov 2026). Shown only once the provider's keys are set on the
 * server; the message starts from the same words as the WhatsApp one and
 * staff can change it before sending. One message, one owner, one press.
 */
export function SmsSender({
  businessId,
  defaultMessage,
}: {
  businessId: string
  defaultMessage: string
}) {
  const t = useT()
  const toast = useToast()
  const status = useQuery({
    queryKey: queryKeys.adminSmsStatus,
    queryFn: adminApi.smsStatus,
    staleTime: 5 * 60_000,
  })
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(defaultMessage)

  const send = useMutation({
    mutationFn: () => adminApi.sendSms(businessId, text),
    onSuccess: () => {
      toast.success(t('adminSms.sent'))
      setOpen(false)
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  if (!status.data?.enabled) return null

  return (
    <div className="space-y-2">
      {!open ? (
        <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
          <MessageSquareText className="h-4 w-4" aria-hidden="true" />
          {t('adminSms.button')}
        </Button>
      ) : (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault()
            send.mutate()
          }}
        >
          <Textarea
            rows={4}
            dir="auto"
            maxLength={1000}
            value={text}
            aria-label={t('adminSms.button')}
            onChange={(event) => setText(event.target.value)}
          />
          <p className="text-xs text-ink-500">
            {t('adminSms.hint', { count: text.length })}
          </p>
          <div className="flex gap-2">
            <Button type="submit" size="sm" loading={send.isPending} disabled={!text.trim()}>
              {t('adminSms.send')}
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
