import { useMutation } from '@tanstack/react-query'
import { Check, Send } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { testimonialApi } from '@/services/api/endpoints'

/**
 * Leaving praise on a listing, with no account.
 *
 * Anonymous on purpose: requiring sign-in kills submissions from the audience
 * this project exists for, and verifying a phone number would imply an
 * independence owner-approved praise does not have. The server rate limits
 * per address and per listing, which is the half that cannot be bypassed.
 *
 * The success state stays on screen instead of resetting the form, because
 * "your testimonial will appear once the owner approves it" is the whole
 * answer to *why has nothing changed on this page* — a form that simply
 * emptied itself would read as a failure.
 */
export function TestimonialForm({ slug }: { slug: string }) {
  const t = useT()
  const toast = useToast()
  const [author, setAuthor] = useState('')
  const [body, setBody] = useState('')
  const [sent, setSent] = useState(false)

  const submit = useMutation({
    mutationFn: () => testimonialApi.submit(slug, { author_name: author, body }),
    onSuccess: (result) => {
      setSent(true)
      // The API's own sentence, in the reader's locale, rather than a
      // generic "thanks": it says the owner decides next.
      toast.success(t('testimonials.sent'), result.message)
    },
    onError: (error) =>
      toast.error(
        t('testimonials.sendFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  if (sent) {
    return (
      <div className="mt-6 flex gap-2.5 rounded-xl border-2 border-olive-200 bg-olive-50 p-4">
        <Check className="mt-0.5 h-5 w-5 shrink-0 text-olive-700" aria-hidden="true" />
        <p className="text-sm leading-relaxed text-olive-900">
          {t('testimonials.sent')} — {t('testimonials.addIntro')}
        </p>
      </div>
    )
  }

  return (
    <form
      className="mt-6 space-y-3 rounded-xl border border-ink-100 bg-sand-50/60 p-4"
      onSubmit={(event) => {
        event.preventDefault()
        submit.mutate()
      }}
    >
      <div>
        <h3 className="font-semibold text-ink-900">{t('testimonials.addHeading')}</h3>
        <p className="mt-0.5 text-sm text-ink-500">{t('testimonials.addIntro')}</p>
      </div>

      <Field label={t('testimonials.authorLabel')} required>
        {(props) => (
          <Input
            {...props}
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
            maxLength={80}
            required
            minLength={2}
          />
        )}
      </Field>

      <Field label={t('testimonials.bodyLabel')} required>
        {(props) => (
          <Textarea
            {...props}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={4}
            maxLength={1000}
            required
            minLength={10}
          />
        )}
      </Field>

      <Button type="submit" loading={submit.isPending}>
        <Send className="h-4 w-4" aria-hidden="true" />
        {t('testimonials.submit')}
      </Button>
    </form>
  )
}
