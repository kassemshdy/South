import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Download, ImageOff, ImagePlus, MousePointerClick, Pencil, Plus, Trash2 } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'

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
import { useCropStep } from '@/features/images/ImageCropDialog'
import { JOB_STATUS_LABELS, JOB_TYPE_LABELS, JobStatusBadge } from '@/features/jobs/JobCard'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { WORK_MODE_LABELS } from '@/pages/JobOfferPage'
import type { AdminJobOpening, JobOpeningInput, JobStatus, JobType, WorkMode } from '@/types/api'
import { formatDate, whatsappHref } from '@/utils/format'

const JOB_TYPES = Object.keys(JOB_TYPE_LABELS) as JobType[]
const JOB_STATUSES = Object.keys(JOB_STATUS_LABELS) as JobStatus[]

interface FormState {
  title: string
  description: string
  employer_name: string
  job_type: JobType
  salary: string
  deadline: string
  location_id: string
  work_place: string
  work_mode: WorkMode | ''
  status: JobStatus
  contact_phone: string
  contact_name: string
  whatsapp_enabled: boolean
}

const NO_MODE = '__none__'

const EMPTY: FormState = {
  title: '',
  description: '',
  employer_name: '',
  job_type: 'FULL_TIME',
  salary: '',
  deadline: '',
  location_id: '',
  work_place: '',
  work_mode: '',
  status: 'ACTIVE',
  contact_phone: '',
  contact_name: '',
  whatsapp_enabled: true,
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
    work_place: blank(form.work_place),
    work_mode: form.work_mode || null,
    status: form.status,
    contact_phone: blank(form.contact_phone),
    contact_name: blank(form.contact_name),
    whatsapp_enabled: form.whatsapp_enabled,
  }
}

/**
 * Job openings (the owners' ticket, 29 Oct 2026): added here by hand and
 * published when ready. Since the jobs redesign (31 Oct 2026) each one has a
 * status, changed right from its row, and counts presses of its WhatsApp and
 * call buttons instead of collecting applications.
 */
export function AdminJobOpeningsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('content')
  const [editing, setEditing] = useState<AdminJobOpening | 'new' | null>(null)
  const [openClicks, setOpenClicks] = useState<string | null>(null)
  const [tab, setTab] = useState<JobStatus | 'ALL'>('ALL')
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const coverCrop = useCropStep('gallery')

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
  const uploadCover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => adminApi.uploadJobOpeningCover(id, file),
    onSuccess: refresh,
    onError: fail,
    onSettled: () => setUploadingId(null),
  })
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: JobStatus }) =>
      adminApi.updateJobOpening(id, { status }),
    onSuccess: refresh,
    onError: fail,
  })
  const removeCover = useMutation({
    mutationFn: (id: string) => adminApi.deleteJobOpeningCover(id),
    onSuccess: refresh,
    onError: fail,
  })

  return (
    <div className="space-y-6">
      {coverCrop.dialog}
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
        <>
        <div role="tablist" className="flex flex-wrap gap-2">
          {(['ALL', ...JOB_STATUSES] as const).map((value) => (
            <Button
              key={value}
              role="tab"
              aria-selected={tab === value}
              size="sm"
              variant={tab === value ? 'primary' : 'outline'}
              onClick={() => setTab(value)}
            >
              {value === 'ALL' ? t('admin.jobStatusAll') : t(JOB_STATUS_LABELS[value])}
              <span className="ltr-nums text-xs opacity-80">
                {(jobs.data ?? []).filter((job) => value === 'ALL' || job.status === value).length}
              </span>
            </Button>
          ))}
        </div>
        <ul className="space-y-3">
          {jobs.data?.filter((job) => tab === 'ALL' || job.status === tab).map((job) => (
            <li key={job.id}>
              <Card>
                <CardBody className="space-y-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    {job.cover_url ? (
                      <img
                        src={job.cover_url}
                        alt=""
                        className="aspect-[16/9] w-28 shrink-0 rounded-lg object-cover"
                      />
                    ) : (
                      <div className="flex aspect-[16/9] w-28 shrink-0 items-center justify-center rounded-lg bg-brand-700 text-white/70">
                        <Briefcase className="h-6 w-6" aria-hidden="true" />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
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
                        <JobStatusBadge status={job.status} className="shadow-none" />
                      </div>
                      <p className="mt-1 text-sm text-ink-500">
                        {t(JOB_TYPE_LABELS[job.job_type])}
                        {job.employer_name ? ` · ${job.employer_name}` : ''}
                        {job.location ? ` · ${job.location.name_ar}` : ''}
                        {job.work_place ? ` · ${job.work_place}` : ''}
                        {job.work_mode ? ` · ${t(WORK_MODE_LABELS[job.work_mode])}` : ''}
                        {job.deadline
                          ? ` · ${t('vacancies.deadline', { date: formatDate(job.deadline, locale) })}`
                          : ''}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOpenClicks(openClicks === job.id ? null : job.id)}
                      >
                        <MousePointerClick className="h-4 w-4" aria-hidden="true" />
                        {t('admin.jobContactClicks', { count: job.contact_clicks })}
                      </Button>
                      {canEdit ? (
                        <>
                          <Select
                            value={job.saved_status}
                            onValueChange={(value) => setStatus.mutate({ id: job.id, status: value as JobStatus })}
                          >
                            <SelectTrigger className="h-9 w-auto min-w-36" aria-label={t('admin.jobStatusLabel')}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {JOB_STATUSES.map((value) => (
                                <SelectItem key={value} value={value}>
                                  {t(JOB_STATUS_LABELS[value])}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
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
                            loading={uploadingId === job.id && uploadCover.isPending}
                            onClick={() => {
                              setUploadingId(job.id)
                              fileRef.current?.click()
                            }}
                          >
                            <ImagePlus className="h-4 w-4" aria-hidden="true" />
                            {t('admin.workshopCover')}
                          </Button>
                          {job.cover_url ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              loading={removeCover.isPending && removeCover.variables === job.id}
                              onClick={() => removeCover.mutate(job.id)}
                            >
                              <ImageOff className="h-4 w-4" aria-hidden="true" />
                              {t('admin.videoPosterRemove')}
                            </Button>
                          ) : null}
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
                  {job.submitter_name ? <OfferedBy job={job} /> : null}
                  {openClicks === job.id ? <ContactClicks job={job} /> : null}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
        </>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          const id = uploadingId
          if (file && id) {
            void coverCrop.crop(file).then((cropped) => {
              if (cropped) uploadCover.mutate({ id, file: cropped })
              else setUploadingId(null)
            })
          }
        }}
      />
    </div>
  )
}

/** Who offered the job on the public form, and their ID for the reviewer. */
function OfferedBy({ job }: { job: AdminJobOpening }) {
  const { t } = useI18n()
  const toast = useToast()
  const canReadId = useStaffCan('documents')
  const download = useMutation({
    mutationFn: () => adminApi.downloadJobOfferIdDocument(job.id),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? 'id'
      link.click()
      URL.revokeObjectURL(url)
    },
    onError: (error) =>
      toast.error(t('admin.downloadDocumentFailed'), error instanceof ApiError ? error.message : undefined),
  })
  const wa = job.submitter_phone ? whatsappHref(job.submitter_phone, '') : null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl bg-sand-50 px-3 py-2 text-sm">
      <span dir="auto">
        {t('admin.jobOfferedBy', { name: job.submitter_name ?? '', phone: job.submitter_phone ?? '' })}
      </span>
      {wa ? (
        <a href={wa} target="_blank" rel="noopener noreferrer" className="font-semibold text-olive-700 hover:underline">
          {t('admin.workshopContact')}
        </a>
      ) : null}
      {canReadId && job.has_id_document ? (
        <Button variant="outline" size="sm" loading={download.isPending} onClick={() => download.mutate()}>
          <Download className="h-4 w-4" aria-hidden="true" />
          {t('admin.jobDownloadId')}
        </Button>
      ) : null}
    </div>
  )
}

/** Presses of the opening's two buttons, all time and per day. */
function ContactClicks({ job }: { job: AdminJobOpening }) {
  const { t, locale } = useI18n()
  const stats = useQuery({
    queryKey: [...queryKeys.adminJobOpenings, 'clicks', job.id],
    queryFn: () => adminApi.jobContactClicks(job.id),
  })
  if (stats.isLoading) return <Skeleton className="h-20 rounded-xl" />
  if (stats.isError) return <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />
  const data = stats.data
  if (!data || data.days.length === 0) return <p className="text-sm text-ink-500">{t('admin.jobClicksNone')}</p>
  return (
    <div className="rounded-xl ring-1 ring-ink-100">
      <p className="flex gap-4 border-b border-ink-100 px-3 py-2 text-sm font-semibold">
        <span>
          {t('admin.jobClicksWhatsapp')}: <span className="ltr-nums">{data.whatsapp}</span>
        </span>
        <span>
          {t('admin.jobClicksCall')}: <span className="ltr-nums">{data.call}</span>
        </span>
      </p>
      <ul className="divide-y divide-ink-100 text-sm">
        {data.days.map((day) => (
          <li key={day.day} className="flex justify-between gap-3 px-3 py-2">
            <span>{formatDate(day.day, locale)}</span>
            <span className="ltr-nums text-ink-500">
              {t('admin.jobClicksWhatsapp')} {day.whatsapp} · {t('admin.jobClicksCall')} {day.call}
            </span>
          </li>
        ))}
      </ul>
    </div>
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
          work_place: job.work_place ?? '',
          work_mode: job.work_mode ?? '',
          status: job.saved_status,
          contact_phone: job.own_contact_phone ?? '',
          contact_name: job.contact_name ?? '',
          whatsapp_enabled: job.whatsapp_enabled,
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
            <Field label={t('admin.jobWorkPlaceLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={200}
                  dir="auto"
                  value={form.work_place}
                  onChange={(event) => set('work_place', event.target.value)}
                />
              )}
            </Field>
            <div>
              <label id="job-mode" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.jobWorkModeLabel')}
              </label>
              <Select
                value={form.work_mode || NO_MODE}
                onValueChange={(value) => set('work_mode', value === NO_MODE ? '' : (value as WorkMode))}
              >
                <SelectTrigger aria-labelledby="job-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_MODE}>{t('admin.jobWorkModeNone')}</SelectItem>
                  {(Object.keys(WORK_MODE_LABELS) as WorkMode[]).map((mode) => (
                    <SelectItem key={mode} value={mode}>
                      {t(WORK_MODE_LABELS[mode])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label id="job-status" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.jobStatusLabel')}
              </label>
              <Select value={form.status} onValueChange={(value) => set('status', value as JobStatus)}>
                <SelectTrigger aria-labelledby="job-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {JOB_STATUSES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {t(JOB_STATUS_LABELS[value])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label={t('admin.jobContactPhoneLabel')} hint={t('admin.jobContactPhoneHint')}>
              {(props) => (
                <Input
                  {...props}
                  type="tel"
                  inputMode="tel"
                  dir="ltr"
                  maxLength={25}
                  value={form.contact_phone}
                  onChange={(event) => set('contact_phone', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.jobContactNameLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={120}
                  dir="auto"
                  value={form.contact_name}
                  onChange={(event) => set('contact_name', event.target.value)}
                />
              )}
            </Field>
            <label className="flex items-center gap-2 self-end pb-3 text-sm font-semibold text-ink-700">
              <input
                type="checkbox"
                checked={form.whatsapp_enabled}
                onChange={(event) => set('whatsapp_enabled', event.target.checked)}
                className="h-4 w-4 accent-brand-700"
              />
              {t('admin.jobWhatsappEnabled')}
            </label>
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
