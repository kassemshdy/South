import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, ArchiveRestore, ImagePlus, Megaphone, Pencil, Plus, Trash2 } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useCropStep } from '@/features/images/ImageCropDialog'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ActivityInput, AdminActivity } from '@/types/api'
import { formatDateTime } from '@/utils/format'

interface FormState {
  title: string
  summary: string
  body: string
  starts_at: string
  ends_at: string
  location: string
  sort_order: string
}

const EMPTY: FormState = {
  title: '',
  summary: '',
  body: '',
  starts_at: '',
  ends_at: '',
  location: '',
  sort_order: '0',
}

/** An ISO instant as the `datetime-local` input wants it, in local time. */
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 16)
}

function toPayload(form: FormState): ActivityInput {
  const blank = (value: string) => (value.trim() ? value.trim() : null)
  return {
    title: form.title.trim(),
    summary: blank(form.summary),
    body: form.body.trim(),
    starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : null,
    ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    location: blank(form.location),
    sort_order: Number.parseInt(form.sort_order, 10) || 0,
  }
}

/**
 * The home page's development activities (the owners' ticket, 29 Oct
 * 2026): written here, each with the photograph the carousel shows, and
 * kept or archived. One without a photograph is not shown anywhere yet.
 */
export function AdminActivitiesPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('content')
  const [editing, setEditing] = useState<AdminActivity | 'new' | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const imageCrop = useCropStep('gallery')

  const activities = useQuery({ queryKey: queryKeys.adminActivities, queryFn: adminApi.activities })
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminActivities })
    void queryClient.invalidateQueries({ queryKey: queryKeys.activities })
  }
  const fail = (error: unknown) =>
    toast.error(t('admin.activityFailed'), error instanceof ApiError ? error.message : undefined)

  const toggleArchive = useMutation({
    mutationFn: (activity: AdminActivity) =>
      adminApi.updateActivity(activity.id, { is_archived: !activity.is_archived }),
    onSuccess: refresh,
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteActivity(id),
    onSuccess: refresh,
    onError: fail,
  })
  const uploadImage = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => adminApi.uploadActivityImage(id, file),
    onSuccess: refresh,
    onError: fail,
    onSettled: () => setUploadingId(null),
  })

  return (
    <div className="space-y-6">
      {imageCrop.dialog}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('admin.activitiesTitle')}</h1>
          <p className="mt-2 text-ink-500">{t('admin.activitiesHint')}</p>
        </div>
        {canEdit && editing === null ? (
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('admin.activityNew')}
          </Button>
        ) : null}
      </header>

      {editing !== null ? (
        <ActivityForm
          activity={editing === 'new' ? null : editing}
          onDone={() => {
            setEditing(null)
            refresh()
          }}
        />
      ) : null}

      {activities.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : activities.isError ? (
        <ErrorState error={activities.error} onRetry={() => void activities.refetch()} />
      ) : (activities.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Megaphone className="h-7 w-7" aria-hidden="true" />}
          title={t('activities.empty')}
        />
      ) : (
        <ul className="space-y-3">
          {activities.data?.map((activity) => (
            <li key={activity.id}>
              <Card>
                <CardBody className="flex flex-wrap items-start gap-4 p-4">
                  {activity.image_url ? (
                    <img
                      src={activity.image_url}
                      alt=""
                      className="h-20 w-32 shrink-0 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="flex h-20 w-32 shrink-0 items-center justify-center rounded-lg bg-sand-100 text-ink-500">
                      <ImagePlus className="h-6 w-6" aria-hidden="true" />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-bold text-ink-900" dir="auto">
                        {activity.title}
                      </p>
                      <Badge
                        className={
                          activity.is_archived
                            ? 'bg-ink-100 text-ink-700'
                            : 'bg-olive-100 text-olive-700'
                        }
                      >
                        {activity.is_archived ? t('admin.activityArchived') : t('admin.activityKept')}
                      </Badge>
                      {!activity.image_url ? (
                        <Badge className="bg-clay-50 text-clay-800">{t('admin.activityNeedsImage')}</Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm text-ink-500">
                      {activity.starts_at ? formatDateTime(activity.starts_at, locale) : t('admin.activityNoDate')}
                      {activity.location ? ` · ${activity.location}` : null}
                    </p>
                  </div>
                  {canEdit ? (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        loading={toggleArchive.isPending && toggleArchive.variables?.id === activity.id}
                        onClick={() => toggleArchive.mutate(activity)}
                      >
                        {activity.is_archived ? (
                          <ArchiveRestore className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <Archive className="h-4 w-4" aria-hidden="true" />
                        )}
                        {activity.is_archived ? t('admin.activityRestore') : t('admin.activityArchive')}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(activity)}>
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        {t('common.edit')}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={uploadingId === activity.id && uploadImage.isPending}
                        onClick={() => {
                          setUploadingId(activity.id)
                          fileRef.current?.click()
                        }}
                      >
                        <ImagePlus className="h-4 w-4" aria-hidden="true" />
                        {t('admin.activityImage')}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-clay-600"
                        onClick={() => {
                          if (window.confirm(t('admin.activityDeleteConfirm'))) {
                            remove.mutate(activity.id)
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        {t('common.delete')}
                      </Button>
                    </div>
                  ) : null}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
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
            void imageCrop.crop(file).then((cropped) => {
              if (cropped) uploadImage.mutate({ id, file: cropped })
              else setUploadingId(null)
            })
          }
        }}
      />
    </div>
  )
}

function ActivityForm({ activity, onDone }: { activity: AdminActivity | null; onDone: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState<FormState>(() =>
    activity
      ? {
          title: activity.title,
          summary: activity.summary ?? '',
          body: activity.body,
          starts_at: toLocalInput(activity.starts_at),
          ends_at: toLocalInput(activity.ends_at),
          location: activity.location ?? '',
          sort_order: String(activity.sort_order),
        }
      : EMPTY,
  )
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const save = useMutation({
    mutationFn: () =>
      activity
        ? adminApi.updateActivity(activity.id, toPayload(form))
        : adminApi.createActivity(toPayload(form)),
    onSuccess: () => {
      toast.success(t('admin.activitySaved'))
      onDone()
    },
    onError: (error) =>
      toast.error(t('admin.activityFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card>
      <CardBody className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <Field label={t('admin.activityTitleLabel')} required>
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
          <Field label={t('admin.activitySummaryLabel')}>
            {(props) => (
              <Input
                {...props}
                maxLength={300}
                dir="auto"
                value={form.summary}
                onChange={(event) => set('summary', event.target.value)}
              />
            )}
          </Field>
          <Field label={t('admin.activityBodyLabel')} required>
            {(props) => (
              <Textarea
                {...props}
                required
                minLength={10}
                rows={6}
                dir="auto"
                value={form.body}
                onChange={(event) => set('body', event.target.value)}
              />
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('admin.activityStartsLabel')}>
              {(props) => (
                <Input
                  {...props}
                  type="datetime-local"
                  dir="ltr"
                  value={form.starts_at}
                  onChange={(event) => set('starts_at', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.activityEndsLabel')}>
              {(props) => (
                <Input
                  {...props}
                  type="datetime-local"
                  dir="ltr"
                  value={form.ends_at}
                  onChange={(event) => set('ends_at', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.activityLocationLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={200}
                  dir="auto"
                  value={form.location}
                  onChange={(event) => set('location', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.activityOrderLabel')} hint={t('admin.activityOrderHint')}>
              {(props) => (
                <Input
                  {...props}
                  type="number"
                  inputMode="numeric"
                  dir="ltr"
                  min={-1000}
                  max={1000}
                  value={form.sort_order}
                  onChange={(event) => set('sort_order', event.target.value)}
                />
              )}
            </Field>
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
