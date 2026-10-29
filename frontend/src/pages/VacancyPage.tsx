import { useMutation, useQuery } from '@tanstack/react-query'
import { Banknote, Briefcase, Building2, CalendarClock, Check, MapPin, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'

import { BackLink } from '@/components/ui/BackLink'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { Turnstile } from '@/components/ui/Turnstile'
import { JOB_TYPE_LABELS } from '@/features/jobs/JobCard'
import { WORK_MODE_LABELS } from '@/pages/JobOfferPage'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { jobApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

/**
 * One opening and its application form: name, email, phone and a CV (PDF or
 * a photo), behind the captcha when one is configured. The application and
 * the CV reach the admin page only.
 */
export function VacancyPage() {
  const { slug = '' } = useParams()
  const { t, locale } = useI18n()
  const toast = useToast()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [cv, setCv] = useState<File | null>(null)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)

  const job = useQuery({
    queryKey: queryKeys.jobOpening(slug),
    queryFn: () => jobApi.bySlug(slug),
    enabled: slug.length > 0,
  })
  const data = job.data
  useSeo({
    title: data ? `${data.title} | ${t('app.name')}` : t('vacancies.title'),
    description: data?.description.slice(0, 160),
    canonicalPath: `/vacancies/${encodeURIComponent(slug)}`,
  })

  const apply = useMutation({
    mutationFn: () =>
      jobApi.apply(slug, { full_name: fullName, email, phone_number: phone }, cv as File, captchaToken),
    onError: (error) =>
      toast.error(t('vacancies.failed'), error instanceof ApiError ? error.message : undefined),
  })

  if (job.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
  }
  if (job.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={job.error} onRetry={() => void job.refetch()} />
      </div>
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (cv) apply.mutate()
  }

  return (
    <article className="container-page py-10">
      <BackLink fallback="/vacancies" />
      <div className="mt-4 grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h1 className="text-2xl sm:text-3xl" dir="auto">
            {data.title}
          </h1>
          <ul className="mt-4 space-y-2 text-ink-700">
            <li className="flex items-center gap-2">
              <Briefcase className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
              {t(JOB_TYPE_LABELS[data.job_type])}
            </li>
            {data.employer_name ? (
              <li className="flex items-center gap-2" dir="auto">
                <Building2 className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                {data.employer_name}
              </li>
            ) : null}
            {data.location ? (
              <li className="flex items-center gap-2">
                <MapPin className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                {data.location.name_ar}
              </li>
            ) : null}
            {data.work_place || data.work_mode ? (
              <li className="flex items-center gap-2" dir="auto">
                <MapPin className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                {[data.work_place, data.work_mode ? t(WORK_MODE_LABELS[data.work_mode]) : null]
                  .filter(Boolean)
                  .join(t('common.listSeparator'))}
              </li>
            ) : null}
            {data.salary ? (
              <li className="flex items-center gap-2" dir="auto">
                <Banknote className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                {data.salary}
              </li>
            ) : null}
            {data.deadline ? (
              <li className="flex items-center gap-2">
                <CalendarClock className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                {t('vacancies.deadline', { date: formatDate(data.deadline, locale) })}
              </li>
            ) : null}
          </ul>
          <p className="mt-6 whitespace-pre-line leading-loose text-ink-700" dir="auto">
            {data.description}
          </p>
        </div>

        <aside>
          <Card>
            <CardBody className="p-5">
              {apply.isSuccess ? (
                <div className="text-center">
                  <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
                  <h2 className="mt-3 text-xl">{t('vacancies.sentTitle')}</h2>
                  <p className="mt-2 text-ink-500">{apply.data.message}</p>
                </div>
              ) : (
                <form onSubmit={submit} className="space-y-4">
                  <h2 className="text-xl">{t('vacancies.applyTitle')}</h2>
                  <Field label={t('vacancies.nameLabel')} required>
                    {(props) => (
                      <Input
                        {...props}
                        required
                        minLength={2}
                        maxLength={80}
                        autoComplete="name"
                        value={fullName}
                        onChange={(event) => setFullName(event.target.value)}
                      />
                    )}
                  </Field>
                  <Field label={t('vacancies.emailLabel')} required>
                    {(props) => (
                      <Input
                        {...props}
                        required
                        type="email"
                        dir="ltr"
                        autoComplete="email"
                        maxLength={254}
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                      />
                    )}
                  </Field>
                  <Field label={t('vacancies.phoneLabel')} required>
                    {(props) => (
                      <Input
                        {...props}
                        required
                        type="tel"
                        inputMode="tel"
                        dir="ltr"
                        autoComplete="tel"
                        minLength={6}
                        maxLength={20}
                        value={phone}
                        onChange={(event) => setPhone(event.target.value)}
                      />
                    )}
                  </Field>
                  <Field label={t('vacancies.cvLabel')} required>
                    {(props) => (
                      <input
                        {...props}
                        required
                        type="file"
                        accept="application/pdf,image/jpeg,image/png"
                        onChange={(event) => setCv(event.target.files?.[0] ?? null)}
                        className="block w-full text-sm text-ink-700 file:me-3 file:rounded-lg file:border-0 file:bg-sand-100 file:px-3 file:py-2 file:font-semibold file:text-brand-800"
                      />
                    )}
                  </Field>
                  <Turnstile onToken={setCaptchaToken} />
                  <Button type="submit" block loading={apply.isPending} disabled={!cv}>
                    <Send className="h-5 w-5" aria-hidden="true" />
                    {t('vacancies.submit')}
                  </Button>
                </form>
              )}
            </CardBody>
          </Card>
        </aside>
      </div>
    </article>
  )
}
