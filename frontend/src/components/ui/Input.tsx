import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

const base =
  'w-full rounded-xl border-2 border-ink-100 bg-white px-4 py-3 text-[15px] text-ink-900 placeholder:text-ink-300 transition-colors focus:border-clay-400 focus:outline-none focus:ring-2 focus:ring-clay-500/20 disabled:bg-ink-50 aria-[invalid=true]:border-clay-500'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      // text-start (not text-right) so the field flips correctly if an English
      // locale is added later.
      className={cn(base, 'text-start', className)}
      aria-invalid={invalid || undefined}
      {...props}
    />
  )
})

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, invalid, rows = 4, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(base, 'resize-y text-start leading-relaxed', className)}
      aria-invalid={invalid || undefined}
      {...props}
    />
  )
})
