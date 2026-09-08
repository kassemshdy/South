import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Bug, Camera, Loader2, Paperclip, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { feedbackApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { FeedbackAttachmentKind, FeedbackPriority } from '@/types/api'
import { FEEDBACK_PRIORITY_KEYS } from '@/utils/format'
import { feedbackTicketSchema, type FeedbackTicketValues } from '@/utils/validation'

const PRIORITIES: FeedbackPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']

/** A file this admin picked to attach, before it has been uploaded. */
interface PendingFile {
  file: File
  kind: FeedbackAttachmentKind
  previewUrl: string | null
}

function kindFor(file: File): FeedbackAttachmentKind {
  return file.type.startsWith('image/') ? 'PHOTO' : 'DOCUMENT'
}

/**
 * Floating "report a bug" button, visible only to signed-in administrators,
 * on every page — public or admin. It replaces messaging a bug over
 * WhatsApp: a screenshot of the current page is captured automatically the
 * moment the button is pressed, before the dialog (which would otherwise
 * cover the very thing being reported) ever renders.
 */
export function FeedbackWidget() {
  const { isAdmin } = useAuth()
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [screenshot, setScreenshot] = useState<File | null>(null)
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null)
  const [files, setFiles] = useState<PendingFile[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const schema = feedbackTicketSchema(t)

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<FeedbackTicketValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: '', description: '', priority: 'MEDIUM' },
  })

  const captureScreenshot = async () => {
    setCapturing(true)
    try {
      const { default: html2canvas } = await import('html2canvas-pro')
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        backgroundColor: '#ffffff',
        // Never capture the widget's own button/dialog.
        ignoreElements: (el) => el.hasAttribute('data-feedback-widget'),
      })
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
      if (blob) {
        const shot = new File([blob], 'screenshot.png', { type: 'image/png' })
        setScreenshot(shot)
        setScreenshotUrl(URL.createObjectURL(shot))
      }
    } catch {
      // A failed capture is not fatal — the report still works without one.
    } finally {
      setCapturing(false)
    }
  }

  const handleOpen = () => {
    setOpen(true)
    void captureScreenshot()
  }

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (!next) {
      reset()
      setScreenshot(null)
      if (screenshotUrl) URL.revokeObjectURL(screenshotUrl)
      setScreenshotUrl(null)
      for (const pending of files) {
        if (pending.previewUrl) URL.revokeObjectURL(pending.previewUrl)
      }
      setFiles([])
    }
  }

  const handleFilesSelected = (selected: FileList | null) => {
    if (!selected) return
    const next: PendingFile[] = Array.from(selected).map((file) => ({
      file,
      kind: kindFor(file),
      previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
    }))
    setFiles((current) => [...current, ...next])
  }

  const removeFile = (index: number) => {
    setFiles((current) => {
      const target = current[index]
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl)
      return current.filter((_, i) => i !== index)
    })
  }

  const submit = useMutation({
    mutationFn: async (values: FeedbackTicketValues) => {
      const ticket = await feedbackApi.create({
        title: values.title,
        description: values.description || null,
        priority: values.priority,
        page_path: window.location.pathname + window.location.search,
        client_context: `${navigator.userAgent} · ${window.innerWidth}×${window.innerHeight}`,
      })
      if (screenshot) {
        await feedbackApi.uploadAttachment(ticket.id, screenshot, 'SCREENSHOT')
      }
      for (const pending of files) {
        await feedbackApi.uploadAttachment(ticket.id, pending.file, pending.kind)
      }
      return ticket
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.feedbackTickets })
      toast.success(t('feedback.reportSent'), t('feedback.reportSentDescription'))
      handleOpenChange(false)
    },
    onError: (error) =>
      toast.error(t('feedback.reportFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const onSubmit = handleSubmit((values) => submit.mutate(values))

  return (
    <>
      <button
        type="button"
        data-feedback-widget
        onClick={handleOpen}
        className="fixed bottom-5 end-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-clay-600 text-white shadow-lift transition-transform hover:scale-105 hover:bg-clay-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2"
        aria-label={t('feedback.reportBug')}
      >
        <Bug className="h-6 w-6" aria-hidden="true" />
      </button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent
          title={t('feedback.reportBug')}
          description={t('feedback.reportBugHint')}
          data-feedback-widget
        >
          <form onSubmit={onSubmit} className="max-h-[75vh] space-y-4 overflow-y-auto pe-1" noValidate>
            <Field label={t('feedback.titleLabel')} required error={errors.title?.message}>
              {(props) => (
                <Input
                  {...props}
                  {...register('title')}
                  placeholder={t('feedback.titlePlaceholder')}
                  invalid={Boolean(errors.title)}
                  autoFocus
                />
              )}
            </Field>

            <Field label={t('feedback.descriptionLabel')} error={errors.description?.message}>
              {(props) => (
                <Textarea
                  {...props}
                  {...register('description')}
                  rows={4}
                  placeholder={t('feedback.descriptionPlaceholder')}
                  invalid={Boolean(errors.description)}
                />
              )}
            </Field>

            {/* Only an admin picks a priority. Asked to rank their own
                problem, everyone reasonably answers "urgent", which makes the
                field carry no information and the board harder to triage —
                so a reporter's ticket comes in at the default and an admin
                decides. */}
            {isAdmin ? (
              <Field label={t('feedback.priorityLabel')}>
                {(props) => (
                  <Controller
                    control={control}
                    name="priority"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger id={props.id}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PRIORITIES.map((priority) => (
                            <SelectItem key={priority} value={priority}>
                              {t(FEEDBACK_PRIORITY_KEYS[priority])}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                )}
              </Field>
            ) : null}

            <div>
              <p className="mb-1.5 text-sm font-semibold text-ink-700">
                {t('feedback.screenshotLabel')}
              </p>
              {capturing ? (
                <div className="flex h-32 items-center justify-center gap-2 rounded-xl border-2 border-dashed border-ink-100 text-ink-500">
                  <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                  {t('feedback.capturingScreenshot')}
                </div>
              ) : screenshotUrl ? (
                <div className="relative overflow-hidden rounded-xl border border-ink-100">
                  <img src={screenshotUrl} alt="" className="max-h-40 w-full object-cover object-top" />
                  <div className="absolute inset-x-0 bottom-0 flex justify-end gap-1.5 bg-ink-900/60 p-1.5">
                    <Button type="button" size="sm" variant="outline" onClick={() => void captureScreenshot()}>
                      <Camera className="h-4 w-4" aria-hidden="true" />
                      {t('feedback.retakeScreenshot')}
                    </Button>
                    <button
                      type="button"
                      onClick={() => {
                        if (screenshotUrl) URL.revokeObjectURL(screenshotUrl)
                        setScreenshot(null)
                        setScreenshotUrl(null)
                      }}
                      className="rounded-md bg-clay-600 p-1.5 text-white"
                      aria-label={t('common.delete')}
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              ) : (
                <Button type="button" variant="outline" size="sm" onClick={() => void captureScreenshot()}>
                  <Camera className="h-4 w-4" aria-hidden="true" />
                  {t('feedback.captureScreenshot')}
                </Button>
              )}
            </div>

            <div>
              <p className="mb-1.5 text-sm font-semibold text-ink-700">
                {t('feedback.attachmentsLabel')}
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                multiple
                className="sr-only"
                onChange={(event) => {
                  handleFilesSelected(event.target.files)
                  event.target.value = ''
                }}
              />
              <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                <Paperclip className="h-4 w-4" aria-hidden="true" />
                {t('feedback.addAttachment')}
              </Button>
              {files.length > 0 ? (
                <ul className="mt-2 space-y-1.5">
                  {files.map((pending, index) => (
                    <li
                      key={`${pending.file.name}-${index}`}
                      className="flex items-center justify-between gap-2 rounded-lg bg-sand-100 px-3 py-2 text-sm"
                    >
                      <span className="truncate">{pending.file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="shrink-0 text-ink-500 hover:text-clay-600"
                        aria-label={t('common.delete')}
                      >
                        <X className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            <Button type="submit" size="lg" block loading={submit.isPending}>
              {t('feedback.submitReport')}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
