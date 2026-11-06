import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Archive,
  ArchiveRestore,
  Crop,
  GalleryHorizontal,
  ImagePlus,
  Megaphone,
  MessageCircle,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  Users,
} from 'lucide-react'
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
import type {
  ActivityInput,
  ActivityKind,
  ActivityRegistrationMode,
  AdminActivity,
} from '@/types/api'
import { formatDateTime, whatsappHref } from '@/utils/format'

interface FormState {
  title: string
  summary: string
  body: string
  starts_at: string
  ends_at: string
  location: string
  /** Kept as stored; the carousel manager now sets the order. */
  sort_order: string
  kind: ActivityKind
  registration_mode: ActivityRegistrationMode
  register_url: string
  register_label: string
  show_calendar: boolean
  in_carousel: boolean
}

const EMPTY: FormState = {
  title: '',
  summary: '',
  body: '',
  starts_at: '',
  ends_at: '',
  location: '',
  sort_order: '0',
  kind: 'ACTIVITY',
  // On the site unless the administrator chooses otherwise (the owners'
  // ticket, 4 Nov 2026).
  registration_mode: 'ON_SITE',
  register_url: '',
  register_label: '',
  show_calendar: true,
  in_carousel: false,
}

export const ACTIVITY_KINDS: ActivityKind[] = ['ACTIVITY', 'CONSULTATION', 'WORKSHOP', 'TRAINING']

const REGISTRATION_MODES: ActivityRegistrationMode[] = ['ON_SITE', 'EXTERNAL', 'NONE']

const SELECT_CLASS =
  'w-full rounded-xl border border-ink-100 bg-white px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none'

/** Empty, or an http(s) address: the same rule the API applies. */
function validLink(value: string): boolean {
  const trimmed = value.trim()
  return !trimmed || /^https?:\/\//i.test(trimmed)
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
    kind: form.kind,
    registration_mode: form.registration_mode,
    register_url: blank(form.register_url),
    register_label: blank(form.register_label),
    show_calendar: form.show_calendar,
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
  const [openRegistrations, setOpenRegistrations] = useState<string | null>(null)
  const imageCrop = useCropStep('gallery')
  const cardCrop = useCropStep('card')
  const [cardBusyId, setCardBusyId] = useState<string | null>(null)

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
    onSuccess: (updated) => {
      // The open form shows the new thumbnail and its carousel state.
      setEditing((current) =>
        current !== null && current !== 'new' && current.id === updated.id ? updated : current,
      )
      refresh()
    },
    onError: fail,
    onSettled: () => setUploadingId(null),
  })

  const showUpdated = (updated: AdminActivity) => {
    setEditing((current) =>
      current !== null && current !== 'new' && current.id === updated.id ? updated : current,
    )
    refresh()
  }
  // The card image is cut from the poster already uploaded: it is fetched
  // back (same origin, /media) and offered to the crop window in 16:9.
  const cropCard = async (activity: AdminActivity) => {
    if (!activity.image_url) return
    setCardBusyId(activity.id)
    try {
      const response = await fetch(activity.image_url)
      if (!response.ok) throw new Error(String(response.status))
      const blob = await response.blob()
      const poster = new File([blob], 'poster.jpg', { type: blob.type || 'image/jpeg' })
      const cropped = await cardCrop.crop(poster)
      if (cropped) showUpdated(await adminApi.uploadActivityCardImage(activity.id, cropped))
    } catch (error) {
      fail(error)
    } finally {
      setCardBusyId(null)
    }
  }
  const resetCard = useMutation({
    mutationFn: (id: string) => adminApi.deleteActivityCardImage(id),
    onSuccess: showUpdated,
    onError: fail,
  })

  return (
    <div className="space-y-6">
      {imageCrop.dialog}
      {cardCrop.dialog}
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
          key={editing === 'new' ? 'new' : `${editing.id}:${editing.image_url ?? ''}`}
          activity={editing === 'new' ? null : editing}
          uploading={
            editing !== 'new' && uploadImage.isPending && uploadingId === editing.id
          }
          onPickImage={(id) => {
            setUploadingId(id)
            fileRef.current?.click()
          }}
          cardBusy={editing !== 'new' && cardBusyId === editing.id}
          resettingCard={editing !== 'new' && resetCard.isPending && resetCard.variables === editing.id}
          onCropCard={(target) => void cropCard(target)}
          onResetCard={(id) => resetCard.mutate(id)}
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
                      src={activity.card_thumb_url ?? activity.image_url}
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
                      {activity.in_carousel ? (
                        <Badge className="bg-sea-50 text-sea-700">
                          <GalleryHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                          {t('adminActivity.inCarouselBadge')}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm text-ink-500">
                      {t(`adminActivity.kind.${activity.kind ?? 'ACTIVITY'}`)} ·{' '}
                      {activity.starts_at ? formatDateTime(activity.starts_at, locale) : t('admin.activityNoDate')}
                      {activity.location ? ` · ${activity.location}` : null}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {activity.registration_mode === 'ON_SITE' || activity.registration_count > 0 ? (
                      <Button
                        variant="outline"
                        size="sm"
                        aria-expanded={openRegistrations === activity.id}
                        onClick={() =>
                          setOpenRegistrations((current) =>
                            current === activity.id ? null : activity.id,
                          )
                        }
                      >
                        <Users className="h-4 w-4" aria-hidden="true" />
                        {t('admin.workshopRegistrations', { count: activity.registration_count })}
                      </Button>
                    ) : null}
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
                      {activity.image_url ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={cardBusyId === activity.id}
                          onClick={() => void cropCard(activity)}
                        >
                          <Crop className="h-4 w-4" aria-hidden="true" />
                          {t('admin.activityCardImage')}
                        </Button>
                      ) : null}
                      {activity.card_image_url ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={resetCard.isPending && resetCard.variables === activity.id}
                          onClick={() => resetCard.mutate(activity.id)}
                        >
                          <RotateCcw className="h-4 w-4" aria-hidden="true" />
                          {t('admin.activityCardImageReset')}
                        </Button>
                      ) : null}
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
                  {openRegistrations === activity.id ? (
                    <div className="w-full">
                      <Registrations activity={activity} />
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

function ActivityForm({
  activity,
  uploading,
  onPickImage,
  cardBusy,
  resettingCard,
  onCropCard,
  onResetCard,
  onDone,
}: {
  activity: AdminActivity | null
  uploading: boolean
  onPickImage: (id: string) => void
  cardBusy: boolean
  resettingCard: boolean
  /** Crop the 16:9 card and link-preview image out of the poster. */
  onCropCard: (activity: AdminActivity) => void
  onResetCard: (id: string) => void
  onDone: () => void
}) {
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
          kind: activity.kind ?? 'ACTIVITY',
          registration_mode: activity.registration_mode ?? 'ON_SITE',
          register_url: activity.register_url ?? '',
          register_label: activity.register_label ?? '',
          show_calendar: activity.show_calendar ?? true,
          in_carousel: activity.in_carousel ?? false,
        }
      : EMPTY,
  )
  const external = form.registration_mode === 'EXTERNAL'
  const linkInvalid = !validLink(form.register_url)
  // An external sign-up needs somewhere to send people.
  const linkMissing = external && !form.register_url.trim()
  const hasImage = Boolean(activity?.image_url)
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const save = useMutation({
    mutationFn: () =>
      activity
        ? adminApi.updateActivity(activity.id, {
            ...toPayload(form),
            // Only sent when it changed, so saving an untouched form never
            // puts back a slide someone took out on the carousel screen.
            ...(form.in_carousel !== activity.in_carousel ? { in_carousel: form.in_carousel } : {}),
          })
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
    if (linkInvalid || linkMissing) return
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
            <Field label={t('adminActivity.kindLabel')}>
              {(props) => (
                <select
                  {...props}
                  className={SELECT_CLASS}
                  value={form.kind}
                  onChange={(event) => set('kind', event.target.value as ActivityKind)}
                >
                  {ACTIVITY_KINDS.map((kind) => (
                    <option key={kind} value={kind}>
                      {t(`adminActivity.kind.${kind}`)}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <Field label={t('adminActivity.registrationModeLabel')}>
              {(props) => (
                <select
                  {...props}
                  className={SELECT_CLASS}
                  value={form.registration_mode}
                  onChange={(event) =>
                    set('registration_mode', event.target.value as ActivityRegistrationMode)
                  }
                >
                  {REGISTRATION_MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {t(`adminActivity.registrationMode.${mode}`)}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            {external ? (
              <Field
                label={t('adminActivity.registerUrlLabel')}
                hint={t('adminActivity.registerUrlHint')}
                required
                error={
                  linkInvalid
                    ? t('adminActivity.registerUrlInvalid')
                    : linkMissing
                      ? t('adminActivity.registerUrlRequired')
                      : undefined
                }
              >
                {(props) => (
                  <Input
                    {...props}
                    required
                    type="url"
                    inputMode="url"
                    dir="ltr"
                    maxLength={500}
                    placeholder="https://"
                    value={form.register_url}
                    onChange={(event) => set('register_url', event.target.value)}
                  />
                )}
              </Field>
            ) : null}
            <Field label={t('adminActivity.registerLabelLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={60}
                  dir="auto"
                  placeholder={t('adminActivity.registerLabelDefault')}
                  value={form.register_label}
                  onChange={(event) => set('register_label', event.target.value)}
                />
              )}
            </Field>
          </div>
          <label className="flex items-start gap-2 text-sm text-ink-700">
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 accent-brand-600"
              checked={form.show_calendar}
              onChange={(event) => set('show_calendar', event.target.checked)}
            />
            <span>
              {t('adminActivity.showCalendarLabel')}
              <span className="block text-xs text-ink-500">{t('adminActivity.showCalendarHint')}</span>
            </span>
          </label>

          <div className="rounded-xl border border-ink-100 p-4">
            <p className="text-sm font-semibold text-ink-900">{t('adminActivity.thumbnailLabel')}</p>
            <p className="text-xs text-ink-500">{t('adminActivity.thumbnailHint')}</p>
            {activity ? (
              <div className="mt-3 flex flex-wrap items-center gap-4">
                {activity.image_url ? (
                  // The whole poster, as its page shows it; the card crop is below.
                  <img
                    src={activity.image_thumb_url ?? activity.image_url}
                    alt=""
                    className="aspect-video w-48 rounded-lg bg-sand-100 object-contain"
                  />
                ) : (
                  <div className="flex aspect-video w-48 items-center justify-center rounded-lg bg-sand-100 text-ink-500">
                    <ImagePlus className="h-6 w-6" aria-hidden="true" />
                  </div>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  loading={uploading}
                  onClick={() => onPickImage(activity.id)}
                >
                  <ImagePlus className="h-4 w-4" aria-hidden="true" />
                  {activity.image_url
                    ? t('adminActivity.thumbnailReplace')
                    : t('adminActivity.thumbnailUpload')}
                </Button>
              </div>
            ) : null}
            {activity?.image_url ? (
              // The 16:9 crop used by the cards, the carousel and link
              // previews; until one is made, they use the poster as it is.
              <div className="mt-3 flex flex-wrap items-center gap-4">
                <img
                  src={activity.card_thumb_url ?? activity.image_url}
                  alt=""
                  className="aspect-video w-48 rounded-lg object-cover"
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={cardBusy}
                    onClick={() => onCropCard(activity)}
                  >
                    <Crop className="h-4 w-4" aria-hidden="true" />
                    {t('admin.activityCardImage')}
                  </Button>
                  {activity.card_image_url ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      loading={resettingCard}
                      onClick={() => onResetCard(activity.id)}
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      {t('admin.activityCardImageReset')}
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}
            {!activity ? (
              <p className="mt-2 text-sm text-ink-500">{t('adminActivity.thumbnailAfterSave')}</p>
            ) : null}
            <label
              className={`mt-4 flex items-start gap-2 text-sm ${
                activity && hasImage ? 'text-ink-700' : 'text-ink-400'
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-brand-600"
                disabled={!activity || !hasImage}
                checked={activity ? form.in_carousel : false}
                onChange={(event) => set('in_carousel', event.target.checked)}
              />
              <span>
                {t('adminActivity.inCarouselLabel')}
                <span className="block text-xs text-ink-500">
                  {!activity
                    ? t('adminActivity.inCarouselAuto')
                    : hasImage
                      ? t('adminActivity.inCarouselAuto')
                      : t('adminActivity.inCarouselNeedsImage')}
                </span>
              </span>
            </label>
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

/** Who signed up on the site, the latest first, each one a WhatsApp tap away. */
function Registrations({ activity }: { activity: AdminActivity }) {
  const { t, locale } = useI18n()
  const rows = useQuery({
    queryKey: queryKeys.adminActivityRegistrations(activity.id),
    queryFn: () => adminApi.activityRegistrations(activity.id),
  })
  if (rows.isLoading) return <Skeleton className="h-20 rounded-xl" />
  if (rows.isError) return <ErrorState error={rows.error} onRetry={() => void rows.refetch()} />
  if ((rows.data ?? []).length === 0) {
    return <p className="text-sm text-ink-500">{t('admin.workshopNoRegistrations')}</p>
  }
  return (
    <ul className="divide-y divide-ink-100 rounded-xl border border-ink-100">
      {rows.data?.map((row) => {
        const href = whatsappHref(
          row.phone_number,
          t('adminActivity.registrationWhatsappMessage', {
            name: row.full_name,
            title: activity.title,
          }),
        )
        return (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
            <span className="min-w-0">
              <span className="font-semibold text-ink-900" dir="auto">
                {row.full_name}
              </span>
              <span className="ltr-nums ms-2 text-sm text-ink-500" dir="ltr">
                {row.phone_number}
              </span>
              <span className="ms-2 text-xs text-ink-500">{formatDateTime(row.created_at, locale)}</span>
            </span>
            {href ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-olive-700 hover:underline"
              >
                <MessageCircle className="h-4 w-4" aria-hidden="true" />
                {t('admin.workshopContact')}
              </a>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}
