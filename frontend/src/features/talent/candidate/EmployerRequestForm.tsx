import { useMutation } from '@tanstack/react-query'
import { Check, Send } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { publicTalentApi } from '@/services/api/endpoints'
import { useServerFieldErrors } from '@/utils/serverFieldErrors'

/**
 * "Have a job for this candidate?" -- replaces the service request form on a
 * job seeker's page. The request is logged for the Janoubona team, who pass
 * it on to the candidate; the success state stays on screen with the API's
 * own sentence, which says so.
 */
export function EmployerRequestForm({ slug, id }: { slug: string; id?: string }) {
  const t = useT()
  const toast = useToast()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [company, setCompany] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState<string | null>(null)
  const { fieldErrors, showErrorsFrom, clearFieldErrors } = useServerFieldErrors()

  const submit = useMutation({
    mutationFn: () =>
      publicTalentApi.employerRequest(slug, {
        employer_name: name,
        phone,
        company: company || undefined,
        job_title: jobTitle || undefined,
        message: message || undefined,
      }),
    onSuccess: (result) => {
      setSent(result.message)
      toast.success(t('candidate.formSent'), result.message)
    },
    onError: (error) => {
      showErrorsFrom(error)
      toast.error(t('candidate.formFailed'), error instanceof ApiError ? error.message : undefined)
    },
  })

  return (
    <section
      id={id}
      className="scroll-mt-24 rounded-2xl border border-ink-100 bg-white p-5 shadow-card"
      aria-labelledby="employer-form-title"
    >
      <h2 id="employer-form-title" className="text-lg font-bold text-ink-900">
        {t('candidate.formTitle')}
      </h2>
      {sent ? (
        <div className="mt-3 flex gap-2.5 rounded-xl border-2 border-olive-200 bg-olive-50 p-4">
          <Check className="mt-0.5 h-5 w-5 shrink-0 text-olive-700" aria-hidden="true" />
          <p className="text-sm leading-relaxed text-olive-900">{sent}</p>
        </div>
      ) : (
        <form
          className="mt-3 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            clearFieldErrors()
            submit.mutate()
          }}
        >
          <p className="text-sm text-ink-500">{t('candidate.formIntro')}</p>
          <Field label={t('candidate.formName')} required error={fieldErrors['employer_name']}>
            {(props) => (
              <Input
                {...props}
                value={name}
                onChange={(event) => setName(event.target.value)}
                invalid={Boolean(fieldErrors['employer_name'])}
                minLength={2}
                maxLength={160}
                required
              />
            )}
          </Field>
          <Field label={t('candidate.formPhone')} required error={fieldErrors['phone']}>
            {(props) => (
              <Input
                {...props}
                type="tel"
                dir="ltr"
                className="ltr-nums"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                invalid={Boolean(fieldErrors['phone'])}
                minLength={6}
                maxLength={25}
                required
              />
            )}
          </Field>
          <Field label={t('candidate.formCompany')} error={fieldErrors['company']}>
            {(props) => (
              <Input
                {...props}
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                maxLength={160}
              />
            )}
          </Field>
          <Field label={t('candidate.formJobTitle')} error={fieldErrors['job_title']}>
            {(props) => (
              <Input
                {...props}
                value={jobTitle}
                onChange={(event) => setJobTitle(event.target.value)}
                maxLength={160}
              />
            )}
          </Field>
          <Field label={t('candidate.formMessage')} error={fieldErrors['message']}>
            {(props) => (
              <Textarea
                {...props}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={3}
                maxLength={1000}
              />
            )}
          </Field>
          <Button type="submit" block loading={submit.isPending}>
            <Send className="h-4 w-4" aria-hidden="true" />
            {t('candidate.formSubmit')}
          </Button>
        </form>
      )}
    </section>
  )
}
