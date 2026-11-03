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
import { Clock, GitBranch, MessageSquare, Paperclip, Plus, Search, Trash2, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useSearchParams } from 'react-router-dom'

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
import {
  FEEDBACK_PRIORITY_KEYS,
  FEEDBACK_STATUS_KEYS,
  formatRelativeDate,
  telHref,
  whatsappHref,
} from '@/utils/format'
import { commentSchema, type CommentValues } from '@/utils/validation'

const STATUSES: FeedbackStatus[] = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'NEEDS_FEEDBACK', 'NEEDS_APPROVAL', 'APPROVED', 'DONE']

/** A colour per column, so the row reads at a glance. */
const STATUS_DOTS: Record<FeedbackStatus, string> = {
  BACKLOG: 'bg-ink-300',
  TODO: 'bg-sky-500',
  IN_PROGRESS: 'bg-amber-500',
  NEEDS_FEEDBACK: 'bg-clay-500',
  NEEDS_APPROVAL: 'bg-violet-500',
  APPROVED: 'bg-olive-500',
  DONE: 'bg-brand-700',
}

/** The card's leading edge: the priority, readable without the badge. */
const PRIORITY_EDGES: Record<FeedbackPriority, string> = {
  LOW: 'border-s-ink-200',
  MEDIUM: 'border-s-olive-400',
  HIGH: 'border-s-clay-400',
  URGENT: 'border-s-clay-600',
}

const PRIORITIES: FeedbackPriority[] = ['URGENT', 'HIGH', 'MEDIUM', 'LOW']

const PRIORITY_TONES: Record<FeedbackPriority, string> = {
  LOW: 'bg-sand-100 text-ink-600',
  MEDIUM: 'bg-olive-100 text-olive-700',
  HIGH: 'bg-clay-100 text-clay-700',
  URGENT: 'bg-clay-600 text-white',
}

/** How many finished tickets the Done column shows before "show all". */
const DONE_SHOWN = 10

/** When a ticket last changed (moving it to Done is a change), for
 * ordering the Done column newest first. */
function doneAt(ticket: FeedbackTicketSummary): string {
  return ticket.updated_at
}

function groupByStatus(
  tickets: FeedbackTicketSummary[],
): Record<FeedbackStatus, FeedbackTicketSummary[]> {
  const grouped: Record<FeedbackStatus, FeedbackTicketSummary[]> = {
    BACKLOG: [],
    TODO: [],
    IN_PROGRESS: [],
    NEEDS_FEEDBACK: [],
    NEEDS_APPROVAL: [],
    APPROVED: [],
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
  // Narrows what the columns show; the order and the drag targets are the
  // whole board's, so moving a card with a filter on puts it where it was.
  const [query, setQuery] = useState('')
  const [priority, setPriority] = useState<FeedbackPriority | null>(null)
  const needle = query.trim().toLowerCase()
  const visible = (ticket: FeedbackTicketSummary) =>
    (!priority || ticket.priority === priority) &&
    (!needle || ticket.title.toLowerCase().includes(needle))
  const total = STATUSES.reduce((sum, status) => sum + columns[status].length, 0)
  // A link from the Telegram copy carries the ticket to open: ?ticket=<id>.
  const [searchParams, setSearchParams] = useSearchParams()
  const [openTicketId, setOpenTicketIdState] = useState<string | null>(() =>
    searchParams.get('ticket'),
  )
  // The Telegram buttons add the decision to confirm: ?decision=approve|reject.
  const [decision] = useState<Decision | null>(() => {
    const value = searchParams.get('decision')
    return value === 'approve' || value === 'reject' ? value : null
  })
  const setOpenTicketId = (id: string | null) => {
    setOpenTicketIdState(id)
    if (!id && (searchParams.has('ticket') || searchParams.has('decision'))) {
      const next = new URLSearchParams(searchParams)
      next.delete('ticket')
      next.delete('decision')
      setSearchParams(next, { replace: true })
    }
  }

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
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('admin.feedbackHeading')}</h1>
          <p className="mt-2 text-ink-500">{t('admin.feedbackSubtitle')}</p>
        </div>
        <span className="ltr-nums rounded-full bg-sand-100 px-3 py-1 text-sm font-semibold text-ink-600">
          {t('feedback.board.total', { count: total })}
        </span>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ink-100 bg-white p-3">
        <label className="relative min-w-[14rem] flex-1">
          <span className="sr-only">{t('feedback.board.search')}</span>
          <Search
            className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('feedback.board.search')}
            className="h-10 w-full rounded-xl border border-ink-200 bg-sand-50 ps-9 pe-3 text-sm focus:border-brand-500 focus:bg-white focus:outline-none"
          />
        </label>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t('feedback.priorityLabel')}>
          <button
            type="button"
            aria-pressed={priority === null}
            onClick={() => setPriority(null)}
            className={`rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ${
              priority === null ? 'bg-brand-800 text-white' : 'bg-sand-100 text-ink-600 hover:bg-sand-200'
            }`}
          >
            {t('feedback.board.allPriorities')}
          </button>
          {PRIORITIES.map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={priority === value}
              onClick={() => setPriority(priority === value ? null : value)}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ${
                priority === value ? 'bg-brand-800 text-white' : 'bg-sand-100 text-ink-600 hover:bg-sand-200'
              }`}
            >
              {t(FEEDBACK_PRIORITY_KEYS[value])}
            </button>
          ))}
        </div>
      </div>

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
          {/* One row of columns that scrolls sideways, as a board does,
              rather than a grid that wraps the last columns under the
              first. Each column scrolls on its own. */}
          <div className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-3 sm:mx-0 sm:snap-none sm:px-0">
            {STATUSES.map((status) => (
              <BoardColumn
                key={status}
                status={status}
                tickets={columns[status]}
                visible={visible}
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
        <TicketDetailDialog
          ticketId={openTicketId}
          decision={openTicketId === searchParams.get('ticket') ? decision : null}
          onClose={() => setOpenTicketId(null)}
        />
      ) : null}
    </div>
  )
}

function BoardColumn({
  status,
  tickets,
  visible,
  onOpenTicket,
}: {
  status: FeedbackStatus
  tickets: FeedbackTicketSummary[]
  visible: (ticket: FeedbackTicketSummary) => boolean
  onOpenTicket: (id: string) => void
}) {
  const t = useT()
  const { setNodeRef, isOver } = useDroppable({ id: status })
  const [showAllDone, setShowAllDone] = useState(false)
  // Done grows without end; the column shows the most recently finished
  // ten unless asked for all (the owners' request, 3 Nov 2026).
  const matching = tickets.filter(visible)
  const limited = status === 'DONE' && !showAllDone && matching.length > DONE_SHOWN
  const shown = limited
    ? [...matching]
        .sort((a, b) => doneAt(b).localeCompare(doneAt(a)))
        .slice(0, DONE_SHOWN)
    : matching

  return (
    <section
      ref={setNodeRef}
      aria-label={t(FEEDBACK_STATUS_KEYS[status])}
      className={`flex max-h-[calc(100dvh-16rem)] w-[85vw] shrink-0 snap-start flex-col rounded-2xl border transition-colors sm:w-auto sm:min-w-[13rem] sm:flex-1 sm:basis-0 ${
        isOver ? 'border-clay-300 bg-clay-50/60' : 'border-ink-100 bg-sand-50'
      }`}
    >
      <h2 className="flex items-center gap-2 border-b border-ink-100 px-3 py-3 text-sm font-bold text-ink-800">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOTS[status]}`} aria-hidden="true" />
        <span className="flex-1 truncate">{t(FEEDBACK_STATUS_KEYS[status])}</span>
        <span className="ltr-nums rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-ink-500 ring-1 ring-ink-100">
          {matching.length === tickets.length ? tickets.length : `${matching.length}/${tickets.length}`}
        </span>
      </h2>
      <SortableContext items={shown.map((ticket) => ticket.id)} strategy={verticalListSortingStrategy}>
        <ul className="flex min-h-[5rem] flex-1 flex-col gap-2 overflow-y-auto p-2">
          {shown.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} onOpen={() => onOpenTicket(ticket.id)} />
          ))}
          {shown.length === 0 ? (
            <li
              className="flex flex-1 items-center justify-center rounded-xl border-2 border-dashed border-ink-100"
              aria-hidden="true"
            />
          ) : null}
        </ul>
      </SortableContext>
      {status === 'DONE' && matching.length > DONE_SHOWN ? (
        <button
          type="button"
          onClick={() => setShowAllDone((value) => !value)}
          className="border-t border-ink-100 px-3 py-2.5 text-sm font-semibold text-brand-700 hover:bg-white"
        >
          {showAllDone
            ? t('feedback.board.showLatestDone', { count: DONE_SHOWN })
            : t('feedback.board.showAllDone', { count: matching.length })}
        </button>
      ) : null}
    </section>
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
  const { t, locale } = useI18n()
  return (
    <div
      className={`rounded-xl border border-s-4 border-ink-100 bg-white p-3 shadow-card transition-shadow hover:shadow-lift ${PRIORITY_EDGES[ticket.priority]} ${dragging ? 'rotate-1 shadow-lift' : ''}`}
    >
      <p className="line-clamp-3 text-sm font-semibold leading-snug text-ink-900" dir="auto">
        {ticket.title}
      </p>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-500">
        <Badge className={PRIORITY_TONES[ticket.priority]}>
          {t(FEEDBACK_PRIORITY_KEYS[ticket.priority])}
        </Badge>
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {formatRelativeDate(ticket.updated_at, locale, t)}
        </span>
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
          <span className="inline-flex min-w-0 items-center gap-1">
            <UserRound className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{ticket.assignee.display_name ?? ticket.assignee.email}</span>
          </span>
        ) : null}
      </div>
    </div>
  )
}

type Decision = 'approve' | 'reject'

function TicketDetailDialog({
  ticketId,
  decision,
  onClose,
}: {
  ticketId: string
  decision: Decision | null
  onClose: () => void
}) {
  const { t, locale } = useI18n()
  // A Telegram link never decides anything on its own: «reject» opens the
  // form for the reason, «approve» still takes a press of the button.
  const [rejecting, setRejecting] = useState(decision === 'reject')
  const [reason, setReason] = useState('')
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

  // The Telegram message's button opens this ticket: approving moves it to
  // APPROVED, which the next release ships.
  const approve = useMutation({
    mutationFn: () => feedbackApi.move(ticketId, 'APPROVED', 0),
    onSuccess: () => {
      invalidate()
      toast.success(t('feedback.approved'))
    },
    onError: (error) =>
      toast.error(t('feedback.approveFailed'), error instanceof ApiError ? error.message : undefined),
  })

  // Rejecting writes the reason on the ticket first, then sends it back to
  // To do -- which starts the triage routine again with that comment to read.
  const reject = useMutation({
    mutationFn: async (body: string) => {
      await feedbackApi.addComment(ticketId, body)
      await feedbackApi.move(ticketId, 'TODO', 0)
    },
    onSuccess: () => {
      invalidate()
      setRejecting(false)
      setReason('')
      toast.success(t('feedback.rejected'))
    },
    onError: (error) =>
      toast.error(t('feedback.rejectFailed'), error instanceof ApiError ? error.message : undefined),
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

            {data.status === 'NEEDS_APPROVAL' ? (
              <div className="space-y-3 rounded-xl bg-olive-50 p-3.5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-ink-700">{t('feedback.approveHint')}</p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      loading={approve.isPending}
                      autoFocus={decision === 'approve'}
                      onClick={() => approve.mutate()}
                    >
                      {t('feedback.approve')}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      aria-expanded={rejecting}
                      onClick={() => setRejecting((open) => !open)}
                    >
                      {t('feedback.reject')}
                    </Button>
                  </div>
                </div>
                {rejecting ? (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault()
                      if (reason.trim()) reject.mutate(reason.trim())
                    }}
                    className="space-y-2"
                    noValidate
                  >
                    <Field label={t('feedback.rejectReasonLabel')}>
                      {(props) => (
                        <Textarea
                          {...props}
                          value={reason}
                          onChange={(event) => setReason(event.target.value)}
                          rows={3}
                          autoFocus
                          placeholder={t('feedback.rejectReasonPlaceholder')}
                        />
                      )}
                    </Field>
                    <Button
                      type="submit"
                      variant="danger"
                      size="sm"
                      loading={reject.isPending}
                      disabled={!reason.trim()}
                    >
                      {t('feedback.rejectConfirm')}
                    </Button>
                  </form>
                ) : null}
              </div>
            ) : null}

            {data.description ? (
              <p className="whitespace-pre-line text-ink-700">{data.description}</p>
            ) : null}

            {data.reporter_contact && (data.reporter_contact.name || data.reporter_contact.phone) ? (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-700">
                <span className="font-semibold">{t('feedback.sentBy')}:</span>
                {data.reporter_contact.name ? <span dir="auto">{data.reporter_contact.name}</span> : null}
                {data.reporter_contact.phone ? (
                  <>
                    <a
                      href={telHref(data.reporter_contact.phone) ?? undefined}
                      className="ltr-nums font-medium text-brand-700 underline-offset-2 hover:underline"
                      dir="ltr"
                    >
                      {data.reporter_contact.phone}
                    </a>
                    {whatsappHref(data.reporter_contact.phone) ? (
                      <a
                        href={whatsappHref(data.reporter_contact.phone) ?? undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-brand-700 underline-offset-2 hover:underline"
                      >
                        WhatsApp
                      </a>
                    ) : null}
                  </>
                ) : null}
              </div>
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
