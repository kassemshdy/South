import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Eye, GalleryHorizontal, GripVertical, ImagePlus, Plus, X } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminCarousel, AdminCarouselSlide } from '@/types/api'
import { formatDate } from '@/utils/format'

const CAROUSEL_KEY = ['admin', 'carousel'] as const

/** Empty, or an http(s) address: the same rule the API applies. */
function validLink(value: string): boolean {
  const trimmed = value.trim()
  return !trimmed || /^https?:\/\//i.test(trimmed)
}

/**
 * «شريط العرض» (the owners' activities ticket, 31 Oct 2026): the slides at
 * the top of the home page and /activities, in one order set here. A slide
 * is an activity's photograph or a custom image with an optional link.
 * Every member of staff reads this screen; content staff change it, and the
 * API enforces that whatever this page shows.
 */
export function AdminCarouselPage() {
  const { t } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canEdit = useStaffCan('content')
  const [picking, setPicking] = useState(false)
  const [adding, setAdding] = useState(false)
  const [previewing, setPreviewing] = useState(false)

  const carousel = useQuery({ queryKey: CAROUSEL_KEY, queryFn: adminApi.carousel })
  const [order, setOrder] = useState<AdminCarouselSlide[]>([])
  useEffect(() => {
    if (carousel.data) setOrder(carousel.data.slides)
  }, [carousel.data])

  const apply = (data: AdminCarousel) => {
    queryClient.setQueryData(CAROUSEL_KEY, data)
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminActivities })
    void queryClient.invalidateQueries({ queryKey: ['carousel'] })
  }
  const fail = (error: unknown) => {
    toast.error(t('adminCarousel.failed'), error instanceof ApiError ? error.message : undefined)
    void carousel.refetch()
  }

  const reorder = useMutation({
    mutationFn: (ids: string[]) => adminApi.reorderCarousel(ids),
    onSuccess: apply,
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteSlide(id),
    onSuccess: apply,
    onError: fail,
  })
  const settings = useMutation({
    mutationFn: (value: boolean) => adminApi.carouselSettings(value),
    onSuccess: apply,
    onError: fail,
  })

  const move = (next: AdminCarouselSlide[]) => {
    setOrder(next)
    reorder.mutate(next.map((slide) => slide.id))
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return
    const from = order.findIndex((slide) => slide.id === active.id)
    const to = order.findIndex((slide) => slide.id === over.id)
    if (from < 0 || to < 0) return
    move(arrayMove(order, from, to))
  }

  const visible = order.filter((slide) => slide.hidden_reason === null)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('adminCarousel.title')}</h1>
          <p className="mt-2 text-ink-500">{t('adminCarousel.intro')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setPreviewing(true)}>
            <Eye className="h-4 w-4" aria-hidden="true" />
            {t('adminCarousel.preview')}
          </Button>
          {canEdit ? (
            <>
              <Button variant="outline" onClick={() => setAdding(true)}>
                <ImagePlus className="h-4 w-4" aria-hidden="true" />
                {t('adminCarousel.custom')}
              </Button>
              <Button onClick={() => setPicking(true)}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t('adminCarousel.add')}
              </Button>
            </>
          ) : null}
        </div>
      </header>

      {carousel.data ? (
        <label className="flex items-center gap-2 text-sm text-ink-700">
          <input
            type="checkbox"
            className="h-4 w-4 accent-brand-600"
            disabled={!canEdit || settings.isPending}
            checked={carousel.data.autoremove_expired}
            onChange={(event) => settings.mutate(event.target.checked)}
          />
          {t('adminCarousel.autoremove')}
        </label>
      ) : null}

      {carousel.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : carousel.isError ? (
        <ErrorState error={carousel.error} onRetry={() => void carousel.refetch()} />
      ) : order.length === 0 ? (
        <EmptyState
          icon={<GalleryHorizontal className="h-7 w-7" aria-hidden="true" />}
          title={t('adminCarousel.empty')}
        />
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={order.map((slide) => slide.id)} strategy={verticalListSortingStrategy}>
            <ol className="space-y-3">
              {order.map((slide, index) => (
                <SlideRow
                  key={slide.id}
                  slide={slide}
                  canEdit={canEdit}
                  first={index === 0}
                  last={index === order.length - 1}
                  onUp={() => move(arrayMove(order, index, index - 1))}
                  onDown={() => move(arrayMove(order, index, index + 1))}
                  onRemove={() => {
                    if (window.confirm(t('adminCarousel.removeConfirm'))) remove.mutate(slide.id)
                  }}
                  onSaved={apply}
                  onFail={fail}
                />
              ))}
            </ol>
          </SortableContext>
        </DndContext>
      )}

      <ActivityPicker
        open={picking}
        onOpenChange={setPicking}
        onAdded={(data) => {
          apply(data)
          setPicking(false)
        }}
        onFail={fail}
      />
      <CustomSlideDialog
        open={adding}
        onOpenChange={setAdding}
        onAdded={(data) => {
          apply(data)
          setAdding(false)
        }}
        onFail={fail}
      />
      <Dialog open={previewing} onOpenChange={setPreviewing}>
        <DialogContent title={t('adminCarousel.preview')} className="max-w-3xl">
          <CarouselPreview slides={visible} />
        </DialogContent>
      </Dialog>
    </div>
  )
}

function SlideRow({
  slide,
  canEdit,
  first,
  last,
  onUp,
  onDown,
  onRemove,
  onSaved,
  onFail,
}: {
  slide: AdminCarouselSlide
  canEdit: boolean
  first: boolean
  last: boolean
  onUp: () => void
  onDown: () => void
  onRemove: () => void
  onSaved: (data: AdminCarousel) => void
  onFail: (error: unknown) => void
}) {
  const { t, locale } = useI18n()
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } = useSortable({
    id: slide.id,
    disabled: !canEdit,
  })
  const [title, setTitle] = useState(slide.title ?? '')
  const [link, setLink] = useState(slide.link_url ?? '')
  const linkInvalid = !validLink(link)
  const save = useMutation({
    mutationFn: () =>
      adminApi.updateCustomSlide(slide.id, {
        title: title.trim() || null,
        link_url: link.trim() || null,
      }),
    onSuccess: onSaved,
    onError: onFail,
  })
  const changed = title !== (slide.title ?? '') || link !== (slide.link_url ?? '')

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={isDragging ? 'relative z-10 opacity-70' : ''}
    >
      <Card>
        <CardBody className="flex flex-wrap items-start gap-3 p-3">
          {canEdit ? (
            <button
              type="button"
              className="mt-6 cursor-grab touch-none rounded p-1 text-ink-400 hover:text-ink-700"
              aria-label={t('adminCarousel.dragHandle')}
              {...attributes}
              {...listeners}
            >
              <GripVertical className="h-5 w-5" aria-hidden="true" />
            </button>
          ) : null}
          <img
            src={slide.image_thumb_url ?? slide.image_url}
            alt=""
            className={`aspect-video w-36 shrink-0 rounded-lg object-cover ${
              slide.hidden_reason ? 'opacity-50' : ''
            }`}
          />
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                className={
                  slide.kind === 'CUSTOM' ? 'bg-clay-50 text-clay-800' : 'bg-olive-100 text-olive-700'
                }
              >
                {slide.kind === 'CUSTOM'
                  ? t('adminCarousel.typeCustom')
                  : t('adminCarousel.typeActivity')}
              </Badge>
              {slide.hidden_reason ? (
                <Badge className="bg-ink-100 text-ink-600">
                  {t(`adminCarousel.hidden.${slide.hidden_reason}`)}
                </Badge>
              ) : null}
            </div>
            {slide.kind === 'CUSTOM' && canEdit ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <Input
                  aria-label={t('adminCarousel.customTitle')}
                  placeholder={t('adminCarousel.customTitle')}
                  maxLength={200}
                  dir="auto"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
                <Input
                  aria-label={t('adminCarousel.customLink')}
                  aria-invalid={linkInvalid}
                  placeholder="https://"
                  type="url"
                  dir="ltr"
                  maxLength={500}
                  value={link}
                  onChange={(event) => setLink(event.target.value)}
                />
                {changed ? (
                  <Button
                    size="sm"
                    className="w-fit"
                    disabled={linkInvalid}
                    loading={save.isPending}
                    onClick={() => save.mutate()}
                  >
                    {t('common.save')}
                  </Button>
                ) : null}
              </div>
            ) : (
              <>
                <p className="font-semibold text-ink-900" dir="auto">
                  {slide.title || slide.link_url || t('adminCarousel.noLink')}
                </p>
                {slide.ends_at ? (
                  <p className="text-sm text-ink-500">
                    {t('adminCarousel.endsOn', { date: formatDate(slide.ends_at, locale) })}
                  </p>
                ) : null}
              </>
            )}
          </div>
          {canEdit ? (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={first}
                aria-label={t('adminCarousel.moveUp')}
                onClick={onUp}
              >
                <ArrowUp className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={last}
                aria-label={t('adminCarousel.moveDown')}
                onClick={onDown}
              >
                <ArrowDown className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-clay-600"
                aria-label={t('adminCarousel.remove')}
                onClick={onRemove}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          ) : null}
        </CardBody>
      </Card>
    </li>
  )
}

function ActivityPicker({
  open,
  onOpenChange,
  onAdded,
  onFail,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdded: (data: AdminCarousel) => void
  onFail: (error: unknown) => void
}) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const activities = useQuery({
    queryKey: queryKeys.adminActivities,
    queryFn: adminApi.activities,
    enabled: open,
  })
  const candidates = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return (activities.data ?? []).filter(
      (activity) =>
        activity.image_url &&
        !activity.is_archived &&
        !activity.in_carousel &&
        (!needle || activity.title.toLowerCase().includes(needle)),
    )
  }, [activities.data, query])
  const add = useMutation({
    mutationFn: (id: string) => adminApi.addActivitySlide(id),
    onSuccess: onAdded,
    onError: onFail,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t('adminCarousel.add')} className="max-w-xl">
        <Input
          aria-label={t('adminCarousel.addSearch')}
          placeholder={t('adminCarousel.addSearch')}
          dir="auto"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {activities.isLoading ? (
          <Skeleton className="mt-4 h-24 rounded-xl" />
        ) : candidates.length === 0 ? (
          <p className="mt-4 text-sm text-ink-500">{t('adminCarousel.addEmpty')}</p>
        ) : (
          <ul className="mt-4 max-h-96 space-y-2 overflow-y-auto">
            {candidates.map((activity) => (
              <li key={activity.id}>
                <button
                  type="button"
                  disabled={add.isPending}
                  onClick={() => add.mutate(activity.id)}
                  className="flex w-full items-center gap-3 rounded-xl border border-ink-100 p-2 text-start hover:bg-sand-50 disabled:opacity-50"
                >
                  <img
                    src={activity.image_thumb_url ?? activity.image_url ?? ''}
                    alt=""
                    className="aspect-video w-24 shrink-0 rounded-md object-cover"
                  />
                  <span className="font-semibold text-ink-900" dir="auto">
                    {activity.title}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  )
}

function CustomSlideDialog({
  open,
  onOpenChange,
  onAdded,
  onFail,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdded: (data: AdminCarousel) => void
  onFail: (error: unknown) => void
}) {
  const { t } = useI18n()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [link, setLink] = useState('')
  const [missing, setMissing] = useState(false)
  const linkInvalid = !validLink(link)
  const add = useMutation({
    mutationFn: (image: File) =>
      adminApi.addCustomSlide(image, title.trim() || null, link.trim() || null),
    onSuccess: (data) => {
      setFile(null)
      setTitle('')
      setLink('')
      onAdded(data)
    },
    onError: onFail,
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!file) {
      setMissing(true)
      return
    }
    if (linkInvalid) return
    add.mutate(file)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t('adminCarousel.custom')} className="max-w-lg">
        <form onSubmit={submit} className="space-y-4">
          <Field
            label={t('adminCarousel.customImage')}
            hint={t('adminActivity.thumbnailHint')}
            error={missing && !file ? t('adminCarousel.customNeedsImage') : undefined}
            required
          >
            {(props) => (
              <input
                {...props}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="block w-full text-sm"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            )}
          </Field>
          <Field label={t('adminCarousel.customTitle')}>
            {(props) => (
              <Input
                {...props}
                maxLength={200}
                dir="auto"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            )}
          </Field>
          <Field
            label={t('adminCarousel.customLink')}
            error={linkInvalid ? t('adminActivity.registerUrlInvalid') : undefined}
          >
            {(props) => (
              <Input
                {...props}
                type="url"
                dir="ltr"
                maxLength={500}
                placeholder="https://"
                value={link}
                onChange={(event) => setLink(event.target.value)}
              />
            )}
          </Field>
          <Button type="submit" loading={add.isPending}>
            {t('adminCarousel.customSave')}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/**
 * The visible slides as visitors meet them: one 16:9 slide at a time, the
 * title over the bottom of the image, previous and next. A stand-in for the
 * public carousel, which reads the public endpoint rather than these rows.
 */
function CarouselPreview({ slides }: { slides: AdminCarouselSlide[] }) {
  const { t } = useI18n()
  const [index, setIndex] = useState(0)
  if (slides.length === 0) {
    return <p className="text-sm text-ink-500">{t('adminCarousel.previewEmpty')}</p>
  }
  const current = slides[Math.min(index, slides.length - 1)]
  if (!current) return null
  const step = (delta: number) => setIndex((index + delta + slides.length) % slides.length)
  return (
    <div className="space-y-3">
      <div className="relative aspect-video overflow-hidden rounded-2xl bg-ink-900">
        <img src={current.image_url} alt="" className="h-full w-full object-cover" />
        {current.title ? (
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4 pt-12">
            <p className="text-xl font-bold text-white" dir="auto">
              {current.title}
            </p>
          </div>
        ) : null}
      </div>
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={() => step(-1)}>
          <ArrowUp className="h-4 w-4 rotate-90" aria-hidden="true" />
        </Button>
        <span className="ltr-nums text-sm text-ink-500">
          {Math.min(index, slides.length - 1) + 1} / {slides.length}
        </span>
        <Button variant="outline" size="sm" onClick={() => step(1)}>
          <ArrowUp className="h-4 w-4 -rotate-90" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
