import {
  DndContext,
  DragOverlay,
  PointerSensor,
  TouchSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch, MessageSquare, Paperclip, Plus, Trash2, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { AttachmentPreview } from '@/features/feedback/AttachmentPreview'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { feedbackApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { FeedbackPriority, FeedbackStatus, FeedbackTicketSummary } from '@/types/api'
import { FEEDBACK_PRIORITY_KEYS, FEEDBACK_STATUS_KEYS, formatRelativeDate } from '@/utils/format'
import { commentSchema, type CommentValues } from '@/utils/validation'

const STATUSES: FeedbackStatus[] = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'DONE']

const PRIORITY_TONES: Record<FeedbackPriority, string> = {
  LOW: 'bg-sand-100 text-ink-600',
  MEDIUM: 'bg-olive-100 text-olive-700',
  HIGH: 'bg-clay-100 text-clay-700',
  URGENT: 'bg-clay-600 text-white',
}

function groupByStatus(
  tickets: FeedbackTicketSummary[],
): Record<FeedbackStatus, FeedbackTicketSummary[]> {
  const grouped: Record<FeedbackStatus, FeedbackTicketSummary[]> = {
    BACKLOG: [],
    TODO: [],
    IN_PROGRESS: [],
    DONE: [],
  }
  for (const ticket of [...tickets].sort((a, b) => a.sort_order - b.sort_order)) {
    grouped[ticket.status].push(ticket)
  }
  return grouped
}

export function AdminFeedbackPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [columns, setColumns] = useState<Record<FeedbackStatus, FeedbackTicketSummary[]>>(
    groupByStatus([]),
  )
  const [activeTicket, setActiveTicket] = useState<FeedbackTicketSummary | null>(null)
  const [openTicketId, setOpenTicketId] = useState<string | null>(null)

  useSeo({ title: t('admin.feedbackHeading'), noIndex: true })

  const board = useQuery({ queryKey: queryKeys.feedbackTickets, queryFn: feedbackApi.list })

  useEffect(() => {
    if (board.data) setColumns(groupByStatus(board.data))
  }, [board.data])

  const move = useMutation({
    mutationFn: ({ id, status, index }: { id: string; status: FeedbackStatus; index: number }) =>
      feedbackApi.move(id, status, index),
    onSuccess: (tickets) => {
      queryClient.setQueryData(queryKeys.feedbackTickets, tickets)
      setColumns(groupByStatus(tickets))
    },
    onError: (error) => {
      toast.error(t('feedback.moveFailed'), error instanceof ApiError ? error.message : undefined)
      void board.refetch()
    },
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } }),
  )

  const findColumnOf = (id: string): FeedbackStatus | undefined =>
    STATUSES.find((status) => columns[status].some((ticket) => ticket.id === id))

  const handleDragStart = (event: DragStartEvent) => {
    const status = findColumnOf(String(event.active.id))
    if (!status) return
    const ticket = columns[status].find((t) => t.id === event.active.id)
    setActiveTicket(ticket ?? null)
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event
    if (!over) return
    const activeId = String(active.id)
    const overId = String(over.id)
    const fromStatus = findColumnOf(activeId)
    const toStatus = STATUSES.includes(overId as FeedbackStatus)
      ? (overId as FeedbackStatus)
      : findColumnOf(overId)
    if (!fromStatus || !toStatus || fromStatus === toStatus) return

    setColumns((current) => {
      const fromItems = [...current[fromStatus]]
      const activeIndex = fromItems.findIndex((ticket) => ticket.id === activeId)
      if (activeIndex === -1) return current
      const [moved] = fromItems.splice(activeIndex, 1)
      if (!moved) return current
      const toItems = [...current[toStatus]]
      const overIndex = toItems.findIndex((ticket) => ticket.id === overId)
      toItems.splice(overIndex >= 0 ? overIndex : toItems.length, 0, {
        ...moved,
        status: toStatus,
      })
      return { ...current, [fromStatus]: fromItems, [toStatus]: toItems }
    })
  }

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveTicket(null)
    const { active, over } = event
    if (!over) return
    const activeId = String(active.id)
    const overId = String(over.id)
    const status = findColumnOf(activeId)
    if (!status) return

    const items = columns[status]
    const activeIndex = items.findIndex((ticket) => ticket.id === activeId)
    const overIndex = items.findIndex((ticket) => ticket.id === overId)
    const targetIndex = overIndex >= 0 ? overIndex : Math.max(items.length - 1, 0)

    if (activeIndex !== -1 && activeIndex !== targetIndex) {
      setColumns((current) => ({
        ...current,
        [status]: arrayMove(current[status], activeIndex, targetIndex),
      }))
    }
    move.mutate({ id: activeId, status, index: targetIndex })
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.feedbackHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.feedbackSubtitle')}</p>
      </header>

      {board.isLoading ? (
        <InlineSpinner />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="grid gap-4 overflow-x-auto pb-2 sm:grid-cols-2 lg:grid-cols-4">
            {STATUSES.map((status) => (
              <BoardColumn
                key={status}
                status={status}
                tickets={columns[status]}
                onOpenTicket={setOpenTicketId}
              />
            ))}
          </div>
          <DragOverlay>
            {activeTicket ? <TicketCardBody ticket={activeTicket} dragging /> : null}
          </DragOverlay>
        </DndContext>
      )}

      {openTicketId ? (
        <TicketDetailDialog ticketId={openTicketId} onClose={() => setOpenTicketId(null)} />
      ) : null}
    </div>
  )
}

function BoardColumn({
  status,
  tickets,
  onOpenTicket,
}: {
  status: FeedbackStatus
  tickets: FeedbackTicketSummary[]
  onOpenTicket: (id: string) => void
}) {
  const t = useT()
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div
      ref={setNodeRef}
      className={`flex min-h-[16rem] flex-col gap-3 rounded-2xl border-2 p-3 transition-colors ${
        isOver ? 'border-clay-300 bg-sand-50' : 'border-ink-100 bg-white'
      }`}
    >
      <h2 className="flex items-center justify-between px-1 text-sm font-bold text-ink-700">
        {t(FEEDBACK_STATUS_KEYS[status])}
        <span className="rounded-full bg-sand-100 px-2 py-0.5 text-xs text-ink-500">
          {tickets.length}
        </span>
      </h2>
      <SortableContext items={tickets.map((ticket) => ticket.id)} strategy={verticalListSortingStrategy}>
        <ul className="flex flex-1 flex-col gap-2">
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} onOpen={() => onOpenTicket(ticket.id)} />
          ))}
        </ul>
      </SortableContext>
    </div>
  )
}

function TicketCard({ ticket, onOpen }: { ticket: FeedbackTicketSummary; onOpen: () => void }) {
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } = useSortable({
    id: ticket.id,
  })

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={isDragging ? 'opacity-40' : ''}
      {...attributes}
      {...listeners}
    >
      <button type="button" onClick={onOpen} className="block w-full text-start">
        <TicketCardBody ticket={ticket} />
      </button>
    </li>
  )
}

function TicketCardBody({
  ticket,
  dragging,
}: {
  ticket: FeedbackTicketSummary
  dragging?: boolean
}) {
  const t = useT()
  return (
    <div
      className={`rounded-xl border border-ink-100 bg-white p-3 shadow-card ${dragging ? 'shadow-lift' : ''}`}
    >
      <div className="mb-1.5 flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-ink-900">{ticket.title}</p>
        <Badge className={PRIORITY_TONES[ticket.priority]}>
          {t(FEEDBACK_PRIORITY_KEYS[ticket.priority])}
        </Badge>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-ink-500">
        {/* Shown as plain text rather than a link: the repository is not
            configured anywhere the frontend can see, and a card that silently
            linked to the wrong repo would be worse than one that does not
            link at all. */}
        {ticket.github_issue_number !== null ? (
          <span className="inline-flex items-center gap-1 font-medium text-ink-700">
            <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />#
            {ticket.github_issue_number}
          </span>
        ) : null}
        {ticket.attachment_count > 0 ? (
          <span className="inline-flex items-center gap-1">
            <Paperclip className="h-3.5 w-3.5" aria-hidden="true" />
            {ticket.attachment_count}
          </span>
        ) : null}
        {ticket.comment_count > 0 ? (
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
            {ticket.comment_count}
          </span>
        ) : null}
        {ticket.assignee ? (
          <span className="inline-flex items-center gap-1 truncate">
            <UserRound className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {ticket.assignee.display_name ?? ticket.assignee.email}
          </span>
        ) : null}
      </div>
    </div>
  )
}

function TicketDetailDialog({ ticketId, onClose }: { ticketId: string; onClose: () => void }) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()

  const ticket = useQuery({
    queryKey: queryKeys.feedbackTicket(ticketId),
    queryFn: () => feedbackApi.get(ticketId),
  })
  const assignees = useQuery({ queryKey: queryKeys.feedbackAssignees, queryFn: feedbackApi.assignees })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.feedbackTicket(ticketId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.feedbackTickets })
  }

  const assign = useMutation({
    mutationFn: (assignee_id: string | null) => feedbackApi.update(ticketId, { assignee_id }),
    onSuccess: invalidate,
  })

  const remove = useMutation({
    mutationFn: () => feedbackApi.remove(ticketId),
    onSuccess: () => {
      invalidate()
      toast.success(t('feedback.ticketDeleted'))
      onClose()
    },
    onError: (error) =>
      toast.error(t('feedback.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const comment = useMutation({
    mutationFn: (body: string) => feedbackApi.addComment(ticketId, body),
    onSuccess: invalidate,
  })

  const schema = useMemo(() => commentSchema(t), [t])
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CommentValues>({ resolver: zodResolver(schema) })

  const data = ticket.data

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent title={data?.title ?? t('feedback.ticketDetails')} className="max-w-2xl">
        {ticket.isLoading || !data ? (
          <InlineSpinner />
        ) : (
          <div className="max-h-[75vh] space-y-5 overflow-y-auto pe-1">
            <div className="flex flex-wrap items-center gap-3 text-sm text-ink-500">
              <Badge className={PRIORITY_TONES[data.priority]}>
                {t(FEEDBACK_PRIORITY_KEYS[data.priority])}
              </Badge>
              <span>{t(FEEDBACK_STATUS_KEYS[data.status])}</span>
              <span>{formatRelativeDate(data.created_at, locale, t)}</span>
            </div>

            {data.description ? (
              <p className="whitespace-pre-line text-ink-700">{data.description}</p>
            ) : null}

            {data.page_path ? (
              <p className="text-sm text-ink-500">
                {t('feedback.reportedFrom')}: <span className="ltr-nums">{data.page_path}</span>
              </p>
            ) : null}
            {data.client_context ? (
              <p className="break-words text-xs text-ink-300">{data.client_context}</p>
            ) : null}

            <div>
              <p className="mb-1.5 text-sm font-semibold text-ink-700">{t('feedback.assigneeLabel')}</p>
              <Select
                value={data.assignee?.id ?? '__unassigned__'}
                onValueChange={(value) =>
                  assign.mutate(value === '__unassigned__' ? null : value)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__unassigned__">{t('feedback.unassigned')}</SelectItem>
                  {assignees.data?.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.display_name ?? user.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {data.attachments.length > 0 ? (
              <div>
                <p className="mb-1.5 text-sm font-semibold text-ink-700">
                  {t('feedback.attachmentsLabel')}
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {data.attachments.map((attachment) => (
                    <AttachmentPreview
                      key={attachment.id}
                      ticketId={ticketId}
                      attachment={attachment}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            <div>
              <p className="mb-1.5 text-sm font-semibold text-ink-700">{t('feedback.commentsLabel')}</p>
              {data.comments.length === 0 ? (
                <p className="text-sm text-ink-500">{t('feedback.noComments')}</p>
              ) : (
                <ul className="space-y-2">
                  {data.comments.map((c) => (
                    <li key={c.id} className="rounded-xl bg-sand-100 p-3 text-sm">
                      <p className="mb-1 flex items-center justify-between gap-2 text-xs font-semibold text-ink-700">
                        <span>{c.author_display_name ?? t('feedback.unassigned')}</span>
                        <span className="font-normal text-ink-300">
                          {formatRelativeDate(c.created_at, locale, t)}
                        </span>
                      </p>
                      <p className="whitespace-pre-line text-ink-700">{c.body}</p>
                    </li>
                  ))}
                </ul>
              )}

              <form
                onSubmit={handleSubmit((values) => {
                  comment.mutate(values.body, { onSuccess: () => reset() })
                })}
                className="mt-3 space-y-2"
                noValidate
              >
                <Field label={t('feedback.addCommentLabel')} error={errors.body?.message}>
                  {(props) => (
                    <Textarea
                      {...props}
                      {...register('body')}
                      rows={2}
                      placeholder={t('feedback.addCommentPlaceholder')}
                      invalid={Boolean(errors.body)}
                    />
                  )}
                </Field>
                <Button type="submit" size="sm" loading={comment.isPending}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  {t('feedback.addCommentAction')}
                </Button>
              </form>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              loading={remove.isPending}
              onClick={() => {
                if (window.confirm(t('feedback.deleteConfirm'))) remove.mutate()
              }}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('feedback.deleteTicket')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
