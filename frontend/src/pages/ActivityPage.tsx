import { useMutation, useQuery } from '@tanstack/react-query'
import {
  CalendarDays,
  CalendarPlus,
  Check,
  ChevronDown,
  Download,
  ExternalLink,
  MapPin,
  Send,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
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
import {
  downloadIcs,
  googleCalendarHref,
  outlookCalendarHref,
} from '@/features/activities/calendar'
import { hasEnded, KIND_KEYS } from '@/features/activities/labels'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { activityApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { Activity } from '@/types/api'
import { formatDateTime } from '@/utils/format'

/**
 * One development activity: its photograph, what it is, when and where,
 * and -- when it has a date -- a way to put it in the visitor's own
 * calendar, as Google Calendar's page or as an `.ics` file for any other.
 *
 * People sign up here, on the page itself, unless the administrator chose an
 * external link or no sign-up (the owners' ticket, 4 Nov 2026). The form is
 * the workshop's: a name and a WhatsApp number, behind the captcha when one
 * is configured, and who signed up reaches the admin page only.
 */
export function ActivityPage() {
  const { slug = '' } = useParams()
  const { t, locale } = useI18n()
  const activity = useQuery({
    queryKey: queryKeys.activity(slug),
    queryFn: () => activityApi.bySlug(slug),
    enabled: slug.length > 0,
  })
  const data = activity.data
  const canonicalPath = `/activities/${encodeURIComponent(slug)}`
  useSeo({
    title: data ? `${data.title} | ${t('app.name')}` : t('activities.title'),
    description: (data?.summary ?? data?.body)?.slice(0, 160),
    canonicalPath,
  })

  if (activity.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
  }
  if (activity.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={activity.error} onRetry={() => void activity.refetch()} />
      </div>
    )
  }

  const pageUrl = `${window.location.origin}${canonicalPath}`
  const ended = hasEnded(data)
  // Both buttons go once it is over (the owners' ticket, 31 Oct 2026).
  const offerCalendar = !ended && data.show_calendar && data.starts_at !== null
  const register =
    !ended && data.registration_mode === 'EXTERNAL' ? data.register_url : null
  const signUpHere = !ended && data.registration_mode === 'ON_SITE'

  return (
    <article className="container-page py-10">
      <BackLink fallback="/activities" />
      <div className="mt-4 grid gap-8 lg:grid-cols-3">
        <div className="min-w-0 lg:col-span-2">
          {data.image_url ? (
            <img
              src={data.image_url}
              alt=""
              className="aspect-[16/9] w-full rounded-2xl object-cover"
            />
          ) : null}
          <p className="mt-6 text-sm font-semibold text-brand-700">{t(KIND_KEYS[data.kind])}</p>
          <h1 className="mt-1 text-2xl sm:text-3xl" dir="auto">
            {data.title}
          </h1>
          {data.summary ? (
            <p className="mt-3 text-lg text-ink-500" dir="auto">
              {data.summary}
            </p>
          ) : null}
          <p className="mt-6 whitespace-pre-line leading-loose text-ink-700" dir="auto">
            {data.body}
          </p>
        </div>

        <aside>
          <Card>
            <CardBody className="space-y-4 p-5">
              {data.starts_at ? (
                <p className="flex items-start gap-2 text-ink-700">
                  <CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  <span>
                    {formatDateTime(data.starts_at, locale)}
                    {data.ends_at ? ` – ${formatDateTime(data.ends_at, locale)}` : null}
                  </span>
                </p>
              ) : null}
              {data.location ? (
                <p className="flex items-start gap-2 text-ink-700" dir="auto">
                  <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  {data.location}
                </p>
              ) : null}
              {ended ? (
                <p className="rounded-xl bg-sand-100 px-4 py-3 font-semibold text-ink-700">
                  {t('activitiesPage.activityEnded')}
                </p>
              ) : null}
              {register || offerCalendar ? (
                <div className="space-y-2 border-t border-ink-100 pt-4">
                  {register ? (
                    <Button asChild block>
                      <a href={register} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-5 w-5" aria-hidden="true" />
                        {data.register_label ?? t('activitiesPage.register')}
                      </a>
                    </Button>
                  ) : null}
                  {offerCalendar ? <CalendarMenu activity={data} pageUrl={pageUrl} /> : null}
                </div>
              ) : null}
              {!data.starts_at && !data.location ? (
                <p className="text-ink-500">{t('activities.noDate')}</p>
              ) : null}
            </CardBody>
          </Card>
          {signUpHere ? <SignUpForm activity={data} /> : null}
        </aside>
      </div>
    </article>
  )
}

/** The sign-up form, in a card of its own under the details. */
function SignUpForm({ activity }: { activity: Activity }) {
  const { t } = useI18n()
  const toast = useToast()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const register = useMutation({
    mutationFn: () =>
      activityApi.register(
        activity.slug,
        { full_name: fullName, phone_number: phone },
        captchaToken,
      ),
    onError: (error) =>
      toast.error(t('workshops.failed'), error instanceof ApiError ? error.message : undefined),
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    register.mutate()
  }

  return (
    <Card className="mt-4">
      <CardBody className="p-5">
        {register.isSuccess ? (
          <div className="text-center">
            <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
            <h2 className="mt-3 text-xl">{t('workshops.sentTitle')}</h2>
            <p className="mt-2 text-ink-500">{register.data.message}</p>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <h2 className="text-xl">{activity.register_label ?? t('activitiesPage.register')}</h2>
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
            <Turnstile onToken={setCaptchaToken} />
            <Button type="submit" block loading={register.isPending}>
              <Send className="h-5 w-5" aria-hidden="true" />
              {t('workshops.submit')}
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  )
}

/** "Add to calendar": Google and Outlook open their own pages; anything else gets an .ics file. */
function CalendarMenu({ activity, pageUrl }: { activity: Activity; pageUrl: string }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const google = googleCalendarHref(activity, pageUrl)
  const outlook = outlookCalendarHref(activity, pageUrl)

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !box.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  const item =
    'flex w-full items-center gap-2 px-4 py-3 text-start text-ink-800 transition-colors hover:bg-sand-50'
  return (
    <div ref={box} className="relative">
      <Button
        type="button"
        variant="outline"
        block
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((value) => !value)}
      >
        <CalendarPlus className="h-5 w-5" aria-hidden="true" />
        {t('activitiesPage.addToCalendar')}
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
      </Button>
      {open ? (
        <div
          role="menu"
          className="absolute inset-x-0 z-20 mt-2 overflow-hidden rounded-xl border border-ink-100 bg-white shadow-lift"
        >
          {google ? (
            <a role="menuitem" href={google} target="_blank" rel="noopener noreferrer" className={item}>
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              {t('activities.googleCalendar')}
            </a>
          ) : null}
          {outlook ? (
            <a role="menuitem" href={outlook} target="_blank" rel="noopener noreferrer" className={item}>
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              {t('activitiesPage.outlook')}
            </a>
          ) : null}
          <button
            role="menuitem"
            type="button"
            className={item}
            onClick={() => {
              downloadIcs(activity, pageUrl)
              setOpen(false)
            }}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            {t('activitiesPage.appleOther')}
          </button>
        </div>
      ) : null}
    </div>
  )
}
