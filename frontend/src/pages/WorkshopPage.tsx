import { useMutation, useQuery } from '@tanstack/react-query'
import { CalendarDays, Check, GraduationCap, MapPin, MonitorPlay, Send } from 'lucide-react'
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
import { workshopPlace } from '@/features/workshops/WorkshopCard'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { workshopApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDateTime, formatPrice } from '@/utils/format'

/**
 * One workshop and its sign-up: a name and a WhatsApp number, behind the
 * captcha when one is configured. Who signed up reaches the admin page only.
 */
export function WorkshopPage() {
  const { slug = '' } = useParams()
  const { t, locale } = useI18n()
  const toast = useToast()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)

  const workshop = useQuery({
    queryKey: queryKeys.workshop(slug),
    queryFn: () => workshopApi.bySlug(slug),
    enabled: slug.length > 0,
  })
  const data = workshop.data
  useSeo({
    title: data ? `${data.title} | ${t('app.name')}` : t('workshops.title'),
    description: data?.description.slice(0, 160),
    canonicalPath: `/workshops/${encodeURIComponent(slug)}`,
  })

  const register = useMutation({
    mutationFn: () =>
      workshopApi.register(slug, { full_name: fullName, phone_number: phone }, captchaToken),
    onError: (error) =>
      toast.error(t('workshops.failed'), error instanceof ApiError ? error.message : undefined),
  })

  if (workshop.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
  }
  if (workshop.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={workshop.error} onRetry={() => void workshop.refetch()} />
      </div>
    )
  }

  const started = new Date(data.starts_at).getTime() < Date.now()
  const price = formatPrice(data.price, data.currency)
  const place = workshopPlace(data, t)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    register.mutate()
  }

  return (
    <article className="container-page py-10">
      <BackLink fallback="/workshops" />
      <div className="mt-4 grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {data.cover_url ? (
            <img src={data.cover_url} alt="" className="aspect-[16/9] w-full rounded-2xl object-cover" />
          ) : (
            <div className="flex aspect-[16/9] w-full items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
              <GraduationCap className="h-16 w-16" aria-hidden="true" />
            </div>
          )}
          <h1 className="mt-6 text-2xl sm:text-3xl" dir="auto">
            {data.title}
          </h1>
          <ul className="mt-4 space-y-2 text-ink-700">
            <li className="flex items-center gap-2">
              <CalendarDays className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
              {formatDateTime(data.starts_at, locale)}
              {data.ends_at ? ` – ${formatDateTime(data.ends_at, locale)}` : null}
            </li>
            {place ? (
              <li className="flex items-center gap-2">
                {data.mode === 'ONLINE' ? (
                  <MonitorPlay className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                ) : (
                  <MapPin className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                )}
                {place}
              </li>
            ) : null}
            {data.trainer_name ? (
              <li dir="auto">{t('workshops.trainer', { name: data.trainer_name })}</li>
            ) : null}
            <li className="font-bold text-brand-800">
              <span className="ltr-nums">{price ?? t('workshops.free')}</span>
            </li>
          </ul>
          <p className="mt-6 whitespace-pre-line leading-loose text-ink-700" dir="auto">
            {data.description}
          </p>
        </div>

        <aside>
          <Card>
            <CardBody className="p-5">
              {register.isSuccess ? (
                <div className="text-center">
                  <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
                  <h2 className="mt-3 text-xl">{t('workshops.sentTitle')}</h2>
                  <p className="mt-2 text-ink-500">{register.data.message}</p>
                </div>
              ) : started ? (
                <p className="text-ink-500">{t('workshops.started')}</p>
              ) : (
                <form onSubmit={submit} className="space-y-4">
                  <h2 className="text-xl">{t('workshops.signUpTitle')}</h2>
                  <Field label={t('workshops.nameLabel')} required>
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
                  <Field label={t('workshops.phoneLabel')} required>
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
                  {data.mode === 'ONLINE' ? (
                    <p className="text-sm text-ink-500">{t('workshops.onlineNote')}</p>
                  ) : null}
                  <Turnstile onToken={setCaptchaToken} />
                  <Button type="submit" block loading={register.isPending}>
                    <Send className="h-5 w-5" aria-hidden="true" />
                    {t('workshops.submit')}
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
