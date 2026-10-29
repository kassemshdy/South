import { useMutation } from '@tanstack/react-query'
import { Building2, Check, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { BackLink } from '@/components/ui/BackLink'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { Turnstile } from '@/components/ui/Turnstile'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { jobApi } from '@/services/api/endpoints'
import type { JobOfferInput, WorkMode } from '@/types/api'

export const WORK_MODE_LABELS: Record<WorkMode, TranslationKey> = {
  REMOTE: 'talent.workModeRemote',
  ON_SITE: 'talent.workModeOnSite',
  BOTH: 'talent.workModeBoth',
}

const EMPTY: JobOfferInput = {
  submitter_name: '',
  phone_number: '',
  employer_name: '',
  work_place: '',
  work_mode: 'ON_SITE',
  title: '',
  description: '',
}

/**
 * An employer offers a job to a southerner (the owners' ticket, 29 Oct
 * 2026): their name, phone and ID, the company, where and how the work is
 * done, the job title and who they are looking for. It arrives as a draft
 * at /admin/job-openings; nothing is published until a person has read it.
 */
export function JobOfferPage() {
  const { t } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState<JobOfferInput>(EMPTY)
  const [idDocument, setIdDocument] = useState<File | null>(null)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  useSeo({
    title: `${t('jobOffer.title')} | ${t('app.name')}`,
    description: t('jobOffer.subtitle'),
    canonicalPath: '/vacancies/offer',
  })
  const set = <K extends keyof JobOfferInput>(key: K, value: JobOfferInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const send = useMutation({
    mutationFn: () => jobApi.offer(form, idDocument as File, captchaToken),
    onError: (error) =>
      toast.error(t('jobOffer.failed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (idDocument) send.mutate()
  }

  const text = (key: keyof JobOfferInput, label: TranslationKey, props: { maxLength: number; type?: string }) => (
    <Field label={t(label)} required>
      {(field) => (
        <Input
          {...field}
          required
          minLength={2}
          maxLength={props.maxLength}
          type={props.type ?? 'text'}
          dir={props.type === 'tel' ? 'ltr' : 'auto'}
          value={form[key]}
          onChange={(event) => set(key, event.target.value as never)}
        />
      )}
    </Field>
  )

  return (
    <div className="container-page max-w-3xl py-10">
      <BackLink fallback="/offer" />
      <header className="mt-4">
        <Building2 className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('jobOffer.title')}</h1>
        <p className="mt-2 text-ink-500">{t('jobOffer.subtitle')}</p>
      </header>
      <Card className="mt-6">
        <CardBody className="p-5">
          {send.isSuccess ? (
            <div className="py-6 text-center">
              <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
              <h2 className="mt-3 text-xl">{t('jobOffer.sentTitle')}</h2>
              <p className="mt-2 text-ink-500">{send.data.message}</p>
              <Link to="/vacancies" className="mt-4 inline-block font-semibold text-brand-700 hover:underline">
                {t('vacancies.title')}
              </Link>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                {text('submitter_name', 'jobOffer.nameLabel', { maxLength: 80 })}
                {text('phone_number', 'jobOffer.phoneLabel', { maxLength: 20, type: 'tel' })}
                {text('employer_name', 'jobOffer.companyLabel', { maxLength: 160 })}
                {text('work_place', 'jobOffer.placeLabel', { maxLength: 200 })}
                <div>
                  <label id="offer-mode" className="mb-1.5 block text-sm font-semibold text-ink-700">
                    {t('jobOffer.modeLabel')}
                    <span className="ms-1 text-clay-500" aria-hidden="true">*</span>
                  </label>
                  <Select value={form.work_mode} onValueChange={(value) => set('work_mode', value as WorkMode)}>
                    <SelectTrigger aria-labelledby="offer-mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(WORK_MODE_LABELS) as WorkMode[]).map((mode) => (
                        <SelectItem key={mode} value={mode}>
                          {t(WORK_MODE_LABELS[mode])}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {text('title', 'jobOffer.jobTitleLabel', { maxLength: 200 })}
              </div>
              <Field label={t('jobOffer.descriptionLabel')} required>
                {(field) => (
                  <Textarea
                    {...field}
                    required
                    minLength={10}
                    maxLength={5000}
                    rows={6}
                    dir="auto"
                    value={form.description}
                    onChange={(event) => set('description', event.target.value)}
                  />
                )}
              </Field>
              <Field label={t('jobOffer.idLabel')} hint={t('jobOffer.idHint')} required>
                {(field) => (
                  <input
                    {...field}
                    required
                    type="file"
                    accept="application/pdf,image/jpeg,image/png"
                    onChange={(event) => setIdDocument(event.target.files?.[0] ?? null)}
                    className="block w-full text-sm text-ink-700 file:me-3 file:rounded-lg file:border-0 file:bg-sand-100 file:px-3 file:py-2 file:font-semibold file:text-brand-800"
                  />
                )}
              </Field>
              <Turnstile onToken={setCaptchaToken} />
              <Button type="submit" loading={send.isPending} disabled={!idDocument}>
                <Send className="h-5 w-5" aria-hidden="true" />
                {t('jobOffer.submit')}
              </Button>
            </form>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
