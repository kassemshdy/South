import { Briefcase, CalendarClock, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { useI18n, type TranslationKey } from '@/i18n'
import type { JobOpening, JobType } from '@/types/api'
import { formatDate } from '@/utils/format'

export const JOB_TYPE_LABELS: Record<JobType, TranslationKey> = {
  FULL_TIME: 'vacancies.type.FULL_TIME',
  PART_TIME: 'vacancies.type.PART_TIME',
  REMOTE: 'vacancies.type.REMOTE',
  FREELANCE: 'vacancies.type.FREELANCE',
  INTERNSHIP: 'vacancies.type.INTERNSHIP',
}

/** One opening in the list: what, for whom, where, and until when. */
export function JobCard({ job }: { job: JobOpening }) {
  const { t, locale } = useI18n()
  return (
    <Link to={`/vacancies/${encodeURIComponent(job.slug)}`} className="block">
      <Card className="h-full overflow-hidden transition-shadow hover:shadow-lift">
        {job.cover_url ? (
          <img src={job.cover_url} alt="" loading="lazy" className="aspect-[16/9] w-full object-cover" />
        ) : null}
        <CardBody className="space-y-2 p-5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sand-100 px-2.5 py-1 text-xs font-semibold text-brand-700">
            <Briefcase className="h-3.5 w-3.5" aria-hidden="true" />
            {t(JOB_TYPE_LABELS[job.job_type])}
          </span>
          <h2 className="text-lg font-bold text-ink-900" dir="auto">
            {job.title}
          </h2>
          {job.employer_name ? (
            <p className="text-sm text-ink-700" dir="auto">
              {job.employer_name}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-500">
            {job.location ? (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-4 w-4" aria-hidden="true" />
                {job.location.name_ar}
              </span>
            ) : null}
            {job.deadline ? (
              <span className="inline-flex items-center gap-1">
                <CalendarClock className="h-4 w-4" aria-hidden="true" />
                {t('vacancies.deadline', { date: formatDate(job.deadline, locale) })}
              </span>
            ) : null}
          </div>
        </CardBody>
      </Card>
    </Link>
  )
}
