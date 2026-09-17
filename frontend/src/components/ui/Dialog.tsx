import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { forwardRef } from 'react'

import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export const DialogContent = forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & { title: string; description?: string }
>(function DialogContent({ className, children, title, description, ...props }, ref) {
  const t = useT()
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-ink-900/40 backdrop-blur-sm" />
      <DialogPrimitive.Content
        ref={ref}
        // `max-h` + `overflow-y-auto` are load-bearing on a phone, not
        // polish. The panel is `fixed` and vertically centred, so a form
        // taller than the viewport hangs off both ends with no way to reach
        // either — and because it is fixed, scrolling the page behind it does
        // not move it. On a Pixel 7 the add-item form's submit button sat
        // below the fold and could not be pressed at all; the acceptance spec
        // caught it as a click that never lands. Anything that makes this
        // panel scroll with the page instead brings that back.
        className={cn(
          'fixed inset-x-4 top-1/2 z-50 mx-auto w-auto max-w-lg -translate-y-1/2 overflow-y-auto rounded-2xl bg-white p-6 shadow-lift focus:outline-none sm:inset-x-0',
          'max-h-[calc(100dvh-2rem)]',
          className,
        )}
        {...props}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <DialogPrimitive.Title className="text-lg font-bold text-ink-900">
              {title}
            </DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className="mt-1 text-sm text-ink-500">
                {description}
              </DialogPrimitive.Description>
            ) : null}
          </div>
          <DialogPrimitive.Close
            className="rounded-lg p-1.5 text-ink-500 transition-colors hover:bg-sand-100 hover:text-ink-900"
            aria-label={t('common.close')}
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </DialogPrimitive.Close>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
})
