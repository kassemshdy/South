import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GraduationCap, ImagePlus, MessageCircle, Pencil, Plus, Trash2, Users } from 'lucide-react'
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
import { useCategories, useLocationGroups } from '@/hooks/useTaxonomy'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminWorkshop, Currency, WorkshopInput, WorkshopMode } from '@/types/api'
import { formatDateTime, formatPrice, whatsappHref } from '@/utils/format'

const NONE = '__none__'

interface FormState {
  title: string
  description: string
  trainer_name: string
  starts_at: string
  ends_at: string
  mode: WorkshopMode
  venue: string
  price: string
  currency: Currency
  category_id: string
  location_id: string
}

const EMPTY: FormState = {
  title: '',
  description: '',
  trainer_name: '',
  starts_at: '',
  ends_at: '',
  mode: 'IN_PERSON',
  venue: '',
  price: '',
  currency: 'USD',
  category_id: '',
  location_id: '',
}

/** An ISO instant as the `datetime-local` input wants it, in local time. */
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 16)
}

function toPayload(form: FormState): WorkshopInput {
  const blank = (value: string) => (value.trim() ? value.trim() : null)
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    trainer_name: blank(form.trainer_name),
    starts_at: new Date(form.starts_at).toISOString(),
    ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    mode: form.mode,
    venue: form.mode === 'IN_PERSON' ? blank(form.venue) : null,
    price: blank(form.price),
    currency: form.currency,
    category_id: form.category_id || null,
    location_id: form.location_id || null,
  }
}

/**
 * The platform's workshops (29 Oct 2026): written here, published by hand,
 * linked to a category and a town so product and article pages show them.
 * Who signed up is listed under each, with a WhatsApp link to reach them.
 */
export function AdminWorkshopsPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('content')
  const [editing, setEditing] = useState<AdminWorkshop | 'new' | null>(null)
  const [openRegistrations, setOpenRegistrations] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const coverCrop = useCropStep('gallery')

  const workshops = useQuery({ queryKey: queryKeys.adminWorkshops, queryFn: adminApi.workshops })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.adminWorkshops })
  const fail = (error: unknown) =>
    toast.error(t('admin.workshopFailed'), error instanceof ApiError ? error.message : undefined)

  const togglePublish = useMutation({
    mutationFn: (workshop: AdminWorkshop) =>
      workshop.is_published
        ? adminApi.unpublishWorkshop(workshop.id)
        : adminApi.publishWorkshop(workshop.id),
    onSuccess: refresh,
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteWorkshop(id),
    onSuccess: refresh,
    onError: fail,
  })
  const uploadCover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => adminApi.uploadWorkshopCover(id, file),
    onSuccess: refresh,
    onError: fail,
    onSettled: () => setUploadingId(null),
  })

  return (
    <div className="space-y-6">
      {coverCrop.dialog}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('admin.workshopsTitle')}</h1>
          <p className="mt-2 text-ink-500">{t('admin.workshopRelatedHint')}</p>
        </div>
        {canEdit && editing === null ? (
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('admin.workshopNew')}
          </Button>
        ) : null}
      </header>

      {editing !== null ? (
        <WorkshopForm
          workshop={editing === 'new' ? null : editing}
          onDone={() => {
            setEditing(null)
            refresh()
          }}
        />
      ) : null}

      {workshops.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : workshops.isError ? (
        <ErrorState error={workshops.error} onRetry={() => void workshops.refetch()} />
      ) : (workshops.data ?? []).length === 0 ? (
        <EmptyState
          icon={<GraduationCap className="h-7 w-7" aria-hidden="true" />}
          title={t('workshops.empty')}
        />
      ) : (
        <ul className="space-y-3">
          {workshops.data?.map((workshop) => (
            <li key={workshop.id}>
              <Card>
                <CardBody className="space-y-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-bold text-ink-900" dir="auto">
                          {workshop.title}
                        </p>
                        <Badge
                          className={
                            workshop.is_published
                              ? 'bg-olive-100 text-olive-700'
                              : 'bg-ink-100 text-ink-700'
                          }
                        >
                          {workshop.is_published
                            ? t('admin.workshopPublished')
                            : t('admin.workshopDraft')}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm text-ink-500">
                        {formatDateTime(workshop.starts_at, locale)} ·{' '}
                        {formatPrice(workshop.price, workshop.currency) ?? t('workshops.free')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setOpenRegistrations((current) =>
                            current === workshop.id ? null : workshop.id,
                          )
                        }
                      >
                        <Users className="h-4 w-4" aria-hidden="true" />
                        {t('admin.workshopRegistrations', { count: workshop.registration_count })}
                      </Button>
                      {canEdit ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            loading={togglePublish.isPending && togglePublish.variables?.id === workshop.id}
                            onClick={() => togglePublish.mutate(workshop)}
                          >
                            {workshop.is_published
                              ? t('admin.workshopUnpublish')
                              : t('admin.workshopPublish')}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setEditing(workshop)}>
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                            {t('common.edit')}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={uploadingId === workshop.id && uploadCover.isPending}
                            onClick={() => {
                              setUploadingId(workshop.id)
                              fileRef.current?.click()
                            }}
                          >
                            <ImagePlus className="h-4 w-4" aria-hidden="true" />
                            {t('admin.workshopCover')}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-clay-600"
                            onClick={() => {
                              if (window.confirm(t('admin.workshopDeleteConfirm'))) {
                                remove.mutate(workshop.id)
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                            {t('common.delete')}
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                  {openRegistrations === workshop.id ? (
                    <Registrations workshop={workshop} />
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

function Registrations({ workshop }: { workshop: AdminWorkshop }) {
  const { t, locale } = useI18n()
  const rows = useQuery({
    queryKey: queryKeys.adminWorkshopRegistrations(workshop.id),
    queryFn: () => adminApi.workshopRegistrations(workshop.id),
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
          t('admin.workshopWhatsappMessage', { name: row.full_name, title: workshop.title }),
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

function WorkshopForm({ workshop, onDone }: { workshop: AdminWorkshop | null; onDone: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const categories = useCategories()
  const { groups } = useLocationGroups()
  const [form, setForm] = useState<FormState>(() =>
    workshop
      ? {
          title: workshop.title,
          description: workshop.description,
          trainer_name: workshop.trainer_name ?? '',
          starts_at: toLocalInput(workshop.starts_at),
          ends_at: toLocalInput(workshop.ends_at),
          mode: workshop.mode,
          venue: workshop.venue ?? '',
          price: workshop.price ?? '',
          currency: workshop.currency,
          category_id: workshop.category?.id ?? '',
          location_id: workshop.location?.id ?? '',
        }
      : EMPTY,
  )
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const save = useMutation({
    mutationFn: () =>
      workshop
        ? adminApi.updateWorkshop(workshop.id, toPayload(form))
        : adminApi.createWorkshop(toPayload(form)),
    onSuccess: () => {
      toast.success(t('admin.workshopSaved'))
      onDone()
    },
    onError: (error) =>
      toast.error(t('admin.workshopFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card>
      <CardBody className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <Field label={t('admin.workshopTitleLabel')} required>
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
          <Field label={t('admin.workshopDescriptionLabel')} required>
            {(props) => (
              <Textarea
                {...props}
                required
                minLength={10}
                rows={6}
                dir="auto"
                value={form.description}
                onChange={(event) => set('description', event.target.value)}
              />
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('admin.workshopStartsLabel')} required>
              {(props) => (
                <Input
                  {...props}
                  type="datetime-local"
                  required
                  dir="ltr"
                  value={form.starts_at}
                  onChange={(event) => set('starts_at', event.target.value)}
                />
              )}
            </Field>
            <Field label={t('admin.workshopEndsLabel')}>
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
            <Field label={t('admin.workshopTrainerLabel')}>
              {(props) => (
                <Input
                  {...props}
                  maxLength={120}
                  dir="auto"
                  value={form.trainer_name}
                  onChange={(event) => set('trainer_name', event.target.value)}
                />
              )}
            </Field>
            <div>
              <label id="workshop-mode" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.workshopModeLabel')}
              </label>
              <Select value={form.mode} onValueChange={(value) => set('mode', value as WorkshopMode)}>
                <SelectTrigger aria-labelledby="workshop-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="IN_PERSON">{t('workshops.inPerson')}</SelectItem>
                  <SelectItem value="ONLINE">{t('workshops.online')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.mode === 'IN_PERSON' ? (
              <Field label={t('admin.workshopVenueLabel')}>
                {(props) => (
                  <Input
                    {...props}
                    maxLength={200}
                    dir="auto"
                    value={form.venue}
                    onChange={(event) => set('venue', event.target.value)}
                  />
                )}
              </Field>
            ) : null}
            <div className="grid grid-cols-[1fr_auto] items-end gap-2">
              <Field label={t('admin.workshopPriceLabel')}>
                {(props) => (
                  <Input
                    {...props}
                    inputMode="decimal"
                    dir="ltr"
                    value={form.price}
                    onChange={(event) => set('price', event.target.value.replace(/[^0-9.]/g, ''))}
                  />
                )}
              </Field>
              <Select value={form.currency} onValueChange={(value) => set('currency', value as Currency)}>
                <SelectTrigger aria-label={t('admin.workshopPriceLabel')} className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="LBP">LBP</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label id="workshop-category" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.workshopCategoryLabel')}
              </label>
              <Select
                value={form.category_id || NONE}
                onValueChange={(value) => set('category_id', value === NONE ? '' : value)}
              >
                <SelectTrigger aria-labelledby="workshop-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>{t('admin.articleNoCategory')}</SelectItem>
                  {(categories.data ?? []).map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name_ar}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label htmlFor="workshop-location" className="mb-1.5 block text-sm font-semibold text-ink-700">
                {t('admin.workshopLocationLabel')}
              </label>
              <LocationCombobox
                id="workshop-location"
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
