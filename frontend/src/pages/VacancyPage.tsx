import { useQuery } from '@tanstack/react-query'
import { Banknote, Briefcase, Building2, CalendarClock, Copy, MapPin, MessageCircle, Phone } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { ShareButton } from '@/components/ui/ShareButton'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import {
  JOB_TYPE_LABELS,
  JobStatusBadge,
  JobThumbnail,
  WORK_MODE_KEYS,
  WorkModeIcon,
  usePostedLabel,
} from '@/features/jobs/JobCard'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { jobApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { JobContactChannel, JobOpening } from '@/types/api'
import { formatDate, telHref, whatsappHref } from '@/utils/format'

/**
 * One opening (the jobs redesign, 31 Oct 2026). Nobody applies through the
 * site any more: the card where the form was carries the number to contact,
 * by WhatsApp or a call. A filled or no-longer-available opening keeps its
 * page, so a shared link still opens, and says it has closed instead.
 */
export function VacancyPage() {
  const { slug = '' } = useParams()
  const { t, locale } = useI18n()
  const posted = usePostedLabel()

  const job = useQuery({
    queryKey: queryKeys.jobOpening(slug),
    queryFn: () => jobApi.bySlug(slug),
    enabled: slug.length > 0,
  })
  const data = job.data
  useSeo({
    title: data ? `${data.title} | ${t('app.name')}` : t('vacancies.title'),
    description: data?.description.slice(0, 160),
    image: data?.cover_url ?? null,
    canonicalPath: `/vacancies/${encodeURIComponent(slug)}`,
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

  const chip = 'inline-flex items-center gap-1.5 rounded-full bg-sand-100 px-3 py-1 text-sm text-ink-700'
  const open = data.status === 'ACTIVE'

  return (
    <article className={`container-page py-10 ${open ? 'pb-28 lg:pb-10' : ''}`}>
      <Link to="/vacancies" className="text-sm font-semibold text-brand-700 hover:underline">
        {t('vacancies.back')}
      </Link>
      <div className="mt-4 grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="relative aspect-video overflow-hidden rounded-2xl">
            <JobThumbnail job={data} className={open ? '' : 'grayscale'} />
          </div>
          <h1 className="mt-6 text-2xl sm:text-3xl" dir="auto">
            {data.title}
          </h1>
          <ul className="mt-4 flex flex-wrap gap-2">
            <li>
              <JobStatusBadge status={data.status} className="shadow-none" />
            </li>
            <li className={chip}>
              <Briefcase className="h-4 w-4 text-clay-600" aria-hidden="true" />
              {t(JOB_TYPE_LABELS[data.job_type])}
            </li>
            {data.work_mode ? (
              <li className={chip}>
                <WorkModeIcon mode={data.work_mode} className="h-4 w-4 text-clay-600" />
                {t(WORK_MODE_KEYS[data.work_mode])}
              </li>
            ) : null}
            {data.location ? (
              <li className={chip}>
                <MapPin className="h-4 w-4 text-clay-600" aria-hidden="true" />
                {data.location.name_ar}
              </li>
            ) : null}
            <li className={chip}>
              <CalendarClock className="h-4 w-4 text-clay-600" aria-hidden="true" />
              {posted(data.created_at)}
            </li>
          </ul>
          {data.employer_name || data.work_place || data.salary ? (
            <ul className="mt-4 space-y-2 text-ink-700">
              {data.employer_name ? (
                <li className="flex items-center gap-2" dir="auto">
                  <Building2 className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  {data.employer_name}
                </li>
              ) : null}
              {data.work_place ? (
                <li className="flex items-center gap-2" dir="auto">
                  <MapPin className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  {data.work_place}
                </li>
              ) : null}
              {data.salary ? (
                <li className="flex items-center gap-2" dir="auto">
                  <Banknote className="h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  {data.salary}
                </li>
              ) : null}
            </ul>
          ) : null}
          <section className="mt-8" aria-labelledby="about-heading">
            <h2 id="about-heading" className="mb-3 text-xl">
              {t('vacancies.aboutHeading')}
            </h2>
            <p className="whitespace-pre-line leading-loose text-ink-700" dir="auto">
              {data.description}
            </p>
          </section>
        </div>

        <aside className="lg:sticky lg:top-[7.75rem] lg:self-start">
          <ContactCard job={data} deadline={data.deadline ? formatDate(data.deadline, locale) : null} />
          <div className="mt-3">
            <ShareButton
              title={data.title}
              text={data.description.slice(0, 160)}
              block
              label={t('vacancies.share')}
            />
          </div>
        </aside>
      </div>

      {open ? <MobileContactBar job={data} /> : null}
    </article>
  )
}

function useContactLinks(job: JobOpening) {
  const { t } = useI18n()
  const url = typeof window === 'undefined' ? '' : window.location.href
  const whatsapp =
    job.whatsapp_enabled && job.contact_phone
      ? whatsappHref(job.contact_phone, t('vacancies.whatsappApply', { title: job.title, url }))
      : null
  const call = telHref(job.contact_phone)
  // Counted, never awaited: the link opens whatever the counter does.
  const count = (channel: JobContactChannel) => {
    void jobApi.contactClick(job.slug, channel).catch(() => undefined)
  }
  return { whatsapp, call, count }
}

function ContactCard({ job, deadline }: { job: JobOpening; deadline: string | null }) {
  const { t } = useI18n()
  const { whatsapp, call, count } = useContactLinks(job)
  const [copied, setCopied] = useState(false)

  if (job.status !== 'ACTIVE') {
    return (
      <Card>
        <CardBody className="space-y-4 p-5 text-center">
          <JobStatusBadge status={job.status} />
          <p className="text-ink-700">
            {job.status === 'FILLED' ? t('vacancies.filledMessage') : t('vacancies.unavailableMessage')}
          </p>
          <Button asChild variant="outline" block>
            <Link to="/vacancies">{t('vacancies.browseOpen')}</Link>
          </Button>
        </CardBody>
      </Card>
    )
  }

  const copy = async () => {
    if (!job.contact_phone) return
    try {
      await navigator.clipboard.writeText(job.contact_phone)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2500)
    } catch {
      /* the number is on screen regardless */
    }
  }

  return (
    <Card className="border-brand-200">
      <CardBody className="space-y-4 p-5">
        <div>
          <h2 className="text-xl">{t('vacancies.applyHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('vacancies.applyInstructions')}</p>
        </div>
        {job.contact_name || job.contact_phone ? (
          <div className="space-y-1">
            {job.contact_name ? (
              <p className="font-semibold text-ink-800" dir="auto">
                {job.contact_name}
              </p>
            ) : null}
            {job.contact_phone ? (
              <div className="flex items-center justify-between gap-2">
                <span className="ltr-nums text-lg font-bold text-ink-900" dir="ltr">
                  {job.contact_phone}
                </span>
                <Button type="button" size="sm" variant="outline" onClick={() => void copy()}>
                  <Copy className="h-4 w-4" aria-hidden="true" />
                  {copied ? t('vacancies.numberCopied') : t('vacancies.copyNumber')}
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
        {whatsapp ? (
          <Button asChild variant="whatsapp" block className="min-h-12 text-base">
            <a href={whatsapp} target="_blank" rel="noopener noreferrer" onClick={() => count('WHATSAPP')}>
              <MessageCircle className="h-5 w-5" aria-hidden="true" />
              {t('business.whatsappCta')}
            </a>
          </Button>
        ) : null}
        {call ? (
          <Button asChild variant="outline" block>
            <a href={call} onClick={() => count('CALL')}>
              <Phone className="h-4 w-4" aria-hidden="true" />
              {t('business.callCta')}
            </a>
          </Button>
        ) : null}
        {deadline ? (
          <p className="text-center text-sm text-ink-500">{t('vacancies.deadline', { date: deadline })}</p>
        ) : null}
      </CardBody>
    </Card>
  )
}

/** On a phone the card scrolls away; both buttons stay under the thumb. */
function MobileContactBar({ job }: { job: JobOpening }) {
  const { t } = useI18n()
  const { whatsapp, call, count } = useContactLinks(job)
  if (!whatsapp && !call) return null
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 gap-2 border-t border-ink-100 bg-white/95 px-4 pb-4 pt-3 shadow-lift backdrop-blur lg:hidden">
      {whatsapp ? (
        <Button asChild variant="whatsapp" block className={call ? 'col-span-2' : 'col-span-3'}>
          <a href={whatsapp} target="_blank" rel="noopener noreferrer" onClick={() => count('WHATSAPP')}>
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            {t('talent.stickyWhatsapp')}
          </a>
        </Button>
      ) : null}
      {call ? (
        <Button asChild variant="outline" block className={whatsapp ? '' : 'col-span-3'}>
          <a href={call} onClick={() => count('CALL')}>
            <Phone className="h-4 w-4" aria-hidden="true" />
            {t('talent.stickyCall')}
          </a>
        </Button>
      ) : null}
    </div>
  )
}
