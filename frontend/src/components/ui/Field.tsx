import { type ReactNode, useId } from 'react'
import { AlertCircle } from 'lucide-react'

import { cn } from '@/utils/cn'

interface FieldProps {
  label: string
  children: (props: { id: string; 'aria-describedby': string | undefined }) => ReactNode
  error?: string | undefined
  hint?: string
  required?: boolean
  className?: string
}

/**
 * Labelled form field wiring up id/aria-describedby so screen readers announce
 * hints and errors with the input they belong to.
 */
export function Field({ label, children, error, hint, required, className }: FieldProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-semibold text-ink-700">
        {label}
        {required ? (
          <span className="ms-1 text-clay-500" aria-hidden="true">
            *
          </span>
        ) : (
          <span className="ms-2 text-xs font-normal text-ink-300">(اختياري)</span>
        )}
      </label>

      {children({ id, 'aria-describedby': describedBy })}

      {hint ? (
        <p id={hintId} className="text-xs text-ink-500">
          {hint}
        </p>
      ) : null}

      {error ? (
        <p id={errorId} role="alert" className="flex items-center gap-1.5 text-sm text-clay-600">
          <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      ) : null}
    </div>
  )
}
