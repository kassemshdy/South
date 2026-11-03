import { Briefcase, Building2, Laptop, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useI18n, type TranslationKey } from '@/i18n'
import type { JobOpening, JobStatus, JobType, WorkMode } from '@/types/api'
import { formatDate } from '@/utils/format'

export const JOB_TYPE_LABELS: Record<JobType, TranslationKey> = {
  FULL_TIME: 'vacancies.type.FULL_TIME',
  PART_TIME: 'vacancies.type.PART_TIME',
  REMOTE: 'vacancies.type.REMOTE',
  FREELANCE: 'vacancies.type.FREELANCE',
  INTERNSHIP: 'vacancies.type.INTERNSHIP',
}

export const JOB_STATUS_LABELS: Record<JobStatus, TranslationKey> = {
  ACTIVE: 'vacancies.status.ACTIVE',
  FILLED: 'vacancies.status.FILLED',
  UNAVAILABLE: 'vacancies.status.UNAVAILABLE',
}

/** Green for open, brown for filled, grey for no longer available. */
export const JOB_STATUS_STYLES: Record<JobStatus, string> = {
  ACTIVE: 'bg-olive-600 text-white',
  FILLED: 'bg-clay-600 text-white',
  UNAVAILABLE: 'bg-ink-500 text-white',
}

/** Work mode has its own icon, never the location pin. */
export function WorkModeIcon({ mode, className }: { mode: WorkMode; className?: string }) {
  const Icon = mode === 'REMOTE' ? Laptop : Building2
  return <Icon className={className} aria-hidden="true" />
}

export function JobStatusBadge({ status, className = '' }: { status: JobStatus; className?: string }) {
  const { t } = useI18n()
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold shadow-card ${JOB_STATUS_STYLES[status]} ${className}`}
    >
      {t(JOB_STATUS_LABELS[status])}
    </span>
  )
}

/** "Today", "1 day ago" ... in Arabic's own number forms; a date after a month. */
export function usePostedLabel(): (iso: string) => string {
  const { t, locale } = useI18n()
  return (iso: string) => {
    const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
    if (days <= 0) return t('vacancies.postedToday')
    if (days === 1) return t('vacancies.postedOneDay')
    if (days === 2) return t('vacancies.postedTwoDays')
    if (days <= 10) return t('vacancies.postedDaysAgo', { count: days })
    if (days <= 30) return t('vacancies.postedManyDays', { count: days })
    return formatDate(iso, locale)
  }
}

/** The opening's thumbnail, or Janoubona green with a briefcase. */
export function JobThumbnail({
  job,
  className = '',
}: {
  job: Pick<JobOpening, 'cover_url'>
  className?: string
}) {
  return job.cover_url ? (
    <img src={job.cover_url} alt="" loading="lazy" className={`h-full w-full object-cover ${className}`} />
  ) : (
    <div className={`flex h-full w-full items-center justify-center bg-brand-700 text-white/70 ${className}`}>
      <Briefcase className="h-12 w-12" aria-hidden="true" />
    </div>
  )
}

/**
 * One opening in the list (the jobs redesign, 31 Oct 2026): its thumbnail
 * with the status in the corner, type and work mode, the title, where and
 * when, and for whom. A closed one is faded.
 */
export function JobCard({ job }: { job: JobOpening }) {
  const { t } = useI18n()
  const posted = usePostedLabel()
  const closed = job.status !== 'ACTIVE'
  return (
    <Link
      to={`/vacancies/${encodeURIComponent(job.slug)}`}
      className={`group flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-lift ${closed ? 'opacity-70' : ''}`}
    >
      <div className="relative aspect-video overflow-hidden">
        <JobThumbnail
          job={job}
          className={`transition-transform duration-300 group-hover:scale-105 ${closed ? 'grayscale' : ''}`}
        />
        <JobStatusBadge status={job.status} className="absolute end-3 top-3" />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-5">
        <div className="flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sand-100 px-2.5 py-1 text-xs font-semibold text-brand-700">
            <Briefcase className="h-3.5 w-3.5" aria-hidden="true" />
            {t(JOB_TYPE_LABELS[job.job_type])}
          </span>
          {job.work_mode ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sand-100 px-2.5 py-1 text-xs font-semibold text-brand-700">
              <WorkModeIcon mode={job.work_mode} className="h-3.5 w-3.5" />
              {t(WORK_MODE_KEYS[job.work_mode])}
            </span>
          ) : null}
        </div>
        <h2 className="line-clamp-2 text-lg font-bold text-ink-900" dir="auto">
          {job.title}
        </h2>
        {job.employer_name ? (
          <p className="text-sm text-ink-700" dir="auto">
            {job.employer_name}
          </p>
        ) : null}
        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-1 text-sm text-ink-500">
          {job.location ? (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4" aria-hidden="true" />
              {job.location.name_ar}
            </span>
          ) : null}
          <span>{posted(job.created_at)}</span>
        </div>
      </div>
    </Link>
  )
}

export const WORK_MODE_KEYS: Record<WorkMode, TranslationKey> = {
  REMOTE: 'talent.workModeRemote',
  ON_SITE: 'talent.workModeOnSite',
  BOTH: 'talent.workModeBoth',
}
