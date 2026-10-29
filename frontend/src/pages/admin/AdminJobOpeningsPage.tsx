import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Download, Pencil, Plus, Trash2, Users } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { JOB_TYPE_LABELS } from '@/features/jobs/JobCard'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminJobOpening, JobOpeningInput, JobType } from '@/types/api'
import { formatDate, formatDateTime, whatsappHref } from '@/utils/format'

const JOB_TYPES = Object.keys(JOB_TYPE_LABELS) as JobType[]

interface FormState {
  title: string
  description: string
  employer_name: string
  job_type: JobType
  salary: string
  deadline: string
  location_id: string
}

const EMPTY: FormState = {
  title: '',
  description: '',
  employer_name: '',
  job_type: 'FULL_TIME',
  salary: '',
  deadline: '',
  location_id: '',
}

function toPayload(form: FormState): JobOpeningInput {
  const blank = (value: string) => (value.trim() ? value.trim() : null)
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    employer_name: blank(form.employer_name),
    job_type: form.job_type,
    salary: blank(form.salary),
    deadline: form.deadline || null,
    location_id: form.location_id || null,
  }
}

/** Is the opening past its last day to apply? */
function isClosed(job: AdminJobOpening): boolean {
  return job.deadline !== null && job.deadline < new Date().toISOString().slice(0, 10)
}

/**
 * Job openings (the owners' ticket, 29 Oct 2026): added here by
 * hand, published when ready, and the applications each one receives, with
 * the CV downloadable by reviewers and the manager.
 */
export function AdminJobOpeningsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('content')
  const [editing, setEditing] = useState<AdminJobOpening | 'new' | null>(null)
  const [openApplications, setOpenApplications] = useState<string | null>(null)

  const jobs = useQuery({ queryKey: queryKeys.adminJobOpenings, queryFn: adminApi.jobOpenings })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.adminJobOpenings })
  const fail = (error: unknown) =>
    toast.error(t('admin.jobFailed'), error instanceof ApiError ? error.message : undefined)

  const togglePublish = useMutation({
    mutationFn: (job: AdminJobOpening) =>
      job.is_published ? adminApi.unpublishJobOpening(job.id) : adminApi.publishJobOpening(job.id),
    onSuccess: refresh,
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteJobOpening(id),
    onSuccess: refresh,
    onError: fail,
  })

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('admin.jobsTitle')}</h1>
          <p className="mt-2 text-ink-500">{t('admin.jobsHint')}</p>
        </div>
        {canEdit && editing === null ? (
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('admin.jobNew')}
          </Button>
        ) : null}
      </header>

      {editing !== null ? (
        <JobForm
          job={editing === 'new' ? null : editing}
          onDone={() => {
            setEditing(null)
            refresh()
          }}
        />
      ) : null}

      {jobs.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
      ) : (jobs.data ?? []).length === 0 ? (
        <EmptyState icon={<Briefcase className="h-7 w-7" aria-hidden="true" />} title={t('vacancies.empty')} />
      ) : (
        <ul className="space-y-3">
          {jobs.data?.map((job) => (
            <li key={job.id}>
              <Card>
                <CardBody className="space-y-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-bold" dir="auto">
                          {job.title}
                        </h2>
                        <Badge
                          className={
                            job.is_published ? 'bg-olive-100 text-olive-700' : 'bg-ink-100 text-ink-700'
                          }
                        >
                          {job.is_published ? t('admin.jobPublished') : t('admin.jobDraft')}
                        </Badge>
                        {isClosed(job) ? (
                          <Badge className="bg-clay-100 text-clay-700">{t('admin.jobClosed')}</Badge>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-ink-500">
                        {t(JOB_TYPE_LABELS[job.job_type])}
                        {job.employer_name ? ` · ${job.employer_name}` : ''}
                        {job.location ? ` · ${job.location.name_ar}` : ''}
                        {job.deadline
                          ? ` · ${t('vacancies.deadline', { date: formatDate(job.deadline, locale) })}`
                          : ''}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOpenApplications(openApplications === job.id ? null : job.id)}
                      >
                        <Users className="h-4 w-4" aria-hidden="true" />
                        {t('admin.jobApplications', { count: job.application_count })}
                      </Button>
                      {canEdit ? (
                        <>
                          <Button
                            size="sm"
                            variant={job.is_published ? 'ghost' : 'primary'}
                            loading={togglePublish.isPending && togglePublish.variables?.id === job.id}
                            onClick={() => togglePublish.mutate(job)}
                          >
                            {job.is_published ? t('admin.jobUnpublish') : t('admin.jobPublish')}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setEditing(job)}>
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                            {t('common.edit')}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label={t('common.delete')}
                            onClick={() => {
                              if (window.confirm(t('admin.jobDeleteConfirm'))) remove.mutate(job.id)
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-clay-700" aria-hidden="true" />
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                  {openApplications === job.id ? <Applications job={job} /> : null}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Applications({ job }: { job: AdminJobOpening }) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canReadCv = useStaffCan('documents')
  const applications = useQuery({
    queryKey: queryKeys.adminJobApplications(job.id),
    queryFn: () => adminApi.jobApplications(job.id),
  })
  const download = useMutation({
    mutationFn: (applicationId: string) => adminApi.downloadJobApplicationCv(job.id, applicationId),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? 'cv'
      link.click()
      URL.revokeObjectURL(url)
    },
    onError: (error) =>
      toast.error(t('admin.downloadDocumentFailed'), error instanceof ApiError ? error.message : undefined),
  })
  const remove = useMutation({
    mutationFn: (applicationId: string) => adminApi.deleteJobApplication(job.id, applicationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminJobApplications(job.id) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminJobOpenings })
    },
    onError: (error) =>
      toast.error(t('admin.jobFailed'), error instanceof ApiError ? error.message : undefined),
  })

  if (applications.isLoading) return <Skeleton className="h-20 rounded-xl" />
  if (applications.isError)
    return <ErrorState error={applications.error} onRetry={() => void applications.refetch()} />
  const rows = applications.data ?? []
  if (rows.length === 0) return <p className="text-sm text-ink-500">{t('admin.jobNoApplications')}</p>

  return (
    <ul className="divide-y divide-ink-100 rounded-xl ring-1 ring-ink-100">
      {rows.map((row) => {
        const wa = whatsappHref(row.phone_number, t('admin.jobWhatsappMessage', { name: row.full_name, title: job.title }))
        return (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
            <div className="min-w-0">
              <p className="font-semibold" dir="auto">
                {row.full_name}
              </p>
              <p className="text-sm text-ink-500" dir="ltr">
                {row.phone_number} · {row.email}
              </p>
              <p className="text-xs text-ink-400">{formatDateTime(row.created_at, locale)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {canReadCv ? (
                <Button
                  variant="outline"
                  size="sm"
                  loading={download.isPending && download.variables === row.id}
                  onClick={() => download.mutate(row.id)}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  {t('admin.jobDownloadCv')}
                </Button>
              ) : null}
              {wa ? (
                <a
                  href={wa}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-9 items-center rounded-xl px-3 text-sm font-semibold text-olive-700 hover:bg-sand-100"
                >
                  {t('admin.workshopContact')}
                </a>
              ) : null}
              <a
                href={`mailto:${row.email}`}
                className="inline-flex min-h-9 items-center rounded-xl px-3 text-sm font-semibold text-brand-700 hover:bg-sand-100"
              >
                {t('admin.jobEmail')}
              </a>
              {canReadCv ? (
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t('common.delete')}
                  onClick={() => {
                    if (window.confirm(t('admin.jobApplicationDeleteConfirm'))) remove.mutate(row.id)
                  }}
                >
                  <Trash2 className="h-4 w-4 text-clay-700" aria-hidden="true" />
                </Button>
              ) : null}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function JobForm({ job, onDone }: { job: AdminJobOpening | null; onDone: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const { groups } = useLocationGroups()
  const [form, setForm] = useState<FormState>(() =>
    job
      ? {
          title: job.title,
          description: job.description,
          employer_name: job.employer_name ?? '',
          job_type: job.job_type,
          salary: job.salary ?? '',
          deadline: job.deadline ?? '',
          location_id: job.location?.id ?? '',
        }
      : EMPTY,
  )
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const save = useMutation({
    mutationFn: () =>
      job ? adminApi.updateJobOpening(job.id, toPayload(form)) : adminApi.createJobOpening(toPayload(form)),
    onSuccess: () => {
      toast.success(t('admin.jobSaved'))
      onDone()
    },
    onError: (error) =>
      toast.error(t('admin.jobFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card>
      <CardBody className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <Field label={t('admin.jobTitleLabel')} required>
            {(props) => (
              <Input
                {...props}
                required
                minLength={3}
                maxLength={200}
                dir="auto"
                value={form.title}
                onChange={(event) => set('title', event.target.value)}
              />
            )}
          </Field>
          <Field label={t('admin.jobDescriptionLabel')} required>
            {(props) => (
              <Textarea
                {...props}
                required
                minLength={10}
                rows={7}
                dir="auto"
                value={form.description}
                onChange={(event) => set('description', event.target.value)}
              />
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('admin.jobEmployerLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={160}
                  dir="auto"
                  value={form.employer_name}
                  onChange={(event) => set('employer_name', event.target.value)}
                />
              )}
            </Field>
            <div>
              <label id="job-type" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.jobTypeLabel')}
              </label>
              <Select value={form.job_type} onValueChange={(value) => set('job_type', value as JobType)}>
                <SelectTrigger aria-labelledby="job-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {JOB_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {t(JOB_TYPE_LABELS[type])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label={t('admin.jobSalaryLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={120}
                  dir="auto"
                  value={form.salary}
                  onChange={(event) => set('salary', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.jobDeadlineLabel')}>
              {(props) => (
                <Input
                  {...props}
                  type="date"
                  dir="ltr"
                  value={form.deadline}
                  onChange={(event) => set('deadline', event.target.value)}
                />
              )}
            </Field>
            <div>
              <label htmlFor="job-location" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.jobLocationLabel')}
              </label>
              <LocationCombobox
                id="job-location"
                value={form.location_id}
                onChange={(id) => set('location_id', id)}
                groups={groups}
                emptyLabel={t('admin.articleNoLocation')}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" loading={save.isPending}>
              {t('common.save')}
            </Button>
            <Button type="button" variant="ghost" onClick={onDone}>
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  )
}
