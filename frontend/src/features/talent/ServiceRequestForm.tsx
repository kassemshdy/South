import { useMutation } from '@tanstack/react-query'
import { Check, Send } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { serviceRequestApi } from '@/services/api/endpoints'
import { useServerFieldErrors } from '@/utils/serverFieldErrors'

/**
 * Asking a talent profile for a piece of work, with no account.
 *
 * The counterpart to the cart on a business page, and it exists to close the
 * same gap the chooser did one layer up: a product could be requested and
 * the request landed in the owner's dashboard, while a craftsperson only
 * ever got a WhatsApp link. A link is fire-and-forget — unsent, or sent and
 * lost in a busy inbox, it leaves no record and the person cannot come back
 * to it a week later.
 *
 * No cart, because there is nothing to collect: a profile has no catalogue,
 * so the description of the work *is* the request, and it is required where
 * an order's note is optional.
 *
 * The WhatsApp button stays on the page beside this. The two are not
 * alternatives — the message gets a faster answer, the stored request is
 * what survives the answer not coming.
 *
 * The success state stays on screen instead of resetting the form: a form
 * that simply emptied itself reads as a failure.
 */
export function ServiceRequestForm({ slug }: { slug: string }) {
  const t = useT()
  const toast = useToast()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [details, setDetails] = useState('')
  const [sent, setSent] = useState(false)
  // The API answers a rejected request with a sentence per bad field; without
  // this the reader got only "check the fields below", which named none.
  const { fieldErrors, showErrorsFrom, clearFieldErrors } = useServerFieldErrors()

  const submit = useMutation({
    mutationFn: () =>
      serviceRequestApi.place(slug, {
        customer_name: name,
        customer_phone: phone,
        details,
      }),
    onSuccess: (result) => {
      setSent(true)
      // The API's own sentence, in the reader's locale, rather than a
      // generic "thanks": it says who will be in touch.
      toast.success(t('serviceRequests.sent'), result.message)
    },
    onError: (error) => {
      showErrorsFrom(error)
      toast.error(
        t('serviceRequests.sendFailed'),
        error instanceof ApiError ? error.message : undefined,
      )
    },
  })

  if (sent) {
    return (
      <div className="flex gap-2.5 rounded-xl border-2 border-olive-200 bg-olive-50 p-4">
        <Check className="mt-0.5 h-5 w-5 shrink-0 text-olive-700" aria-hidden="true" />
        <p className="text-sm leading-relaxed text-olive-900">
          {t('serviceRequests.sent')} — {t('serviceRequests.sentHint')}
        </p>
      </div>
    )
  }

  return (
    <form
      className="space-y-3 rounded-xl border border-ink-100 bg-sand-50/60 p-4"
      onSubmit={(event) => {
        event.preventDefault()
        clearFieldErrors()
        submit.mutate()
      }}
    >
      <div>
        <h2 className="font-semibold text-ink-900">{t('serviceRequests.askHeading')}</h2>
        <p className="mt-0.5 text-sm text-ink-500">{t('serviceRequests.askIntro')}</p>
      </div>

      <Field label={t('serviceRequests.nameLabel')} required error={fieldErrors['customer_name']}>
        {(props) => (
          <Input
            {...props}
            value={name}
            onChange={(event) => setName(event.target.value)}
            invalid={Boolean(fieldErrors['customer_name'])}
            maxLength={80}
            minLength={2}
            required
          />
        )}
      </Field>

      <Field label={t('serviceRequests.phoneLabel')} required error={fieldErrors['customer_phone']}>
        {(props) => (
          <Input
            {...props}
            type="tel"
            dir="ltr"
            className="ltr-nums"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            invalid={Boolean(fieldErrors['customer_phone'])}
            maxLength={20}
            minLength={6}
            required
          />
        )}
      </Field>

      <Field label={t('serviceRequests.detailsLabel')} required error={fieldErrors['details']}>
        {(props) => (
          <Textarea
            {...props}
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            invalid={Boolean(fieldErrors['details'])}
            placeholder={t('serviceRequests.detailsPlaceholder')}
            rows={4}
            maxLength={1000}
            minLength={10}
            required
          />
        )}
      </Field>

      <Button type="submit" block loading={submit.isPending}>
        <Send className="h-4 w-4" aria-hidden="true" />
        {t('serviceRequests.submit')}
      </Button>
    </form>
  )
}
