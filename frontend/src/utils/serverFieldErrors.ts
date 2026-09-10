import { useCallback, useEffect, useState } from 'react'
import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { ApiError } from '@/services/api/client'

/**
 * Putting a 422's per-field sentences back on the fields they belong to.
 *
 * The API has always answered a rejected form with one sentence per bad
 * field, under `error.details.fields`, keyed by the field's own name —
 * `app/core/validation_messages.py` builds it, in the reader's locale. The
 * client parsed it into `ApiError.fields` and then nothing read it: every
 * form showed only the envelope ("check the fields below"), which named no
 * field, so "below" was a guess. On the wizard's twelve-input step that is
 * not a small guess.
 *
 * Two shapes because the forms here come in two kinds: react-hook-form for
 * the long ones, plain `useState` for the short ones. Both end up feeding
 * `Field`'s `error` prop, which already wires `aria-describedby` and
 * `role="alert"` — so a screen reader announces the server's objection with
 * the input it is about, exactly as it does a client-side one.
 */

/** The per-field sentences a 422 carries, keyed by field name. */
export function serverFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {}
  const map: Record<string, string> = {}
  for (const { field, message } of error.fields) {
    // First wins: pydantic can report two failures on one field (missing
    // *and* too short on the same submission), and the first is the one
    // that explains the others.
    if (!(field in map)) map[field] = message
  }
  return map
}

/**
 * Apply a 422 onto a react-hook-form.
 *
 * Returns the messages that had no field to land on, so the caller can still
 * show them rather than swallow them: `setError` on a name the form does not
 * render succeeds silently and the sentence is never seen, which is the same
 * bug this function exists to fix. Membership is tested against the form's
 * own values, so nothing has to hand-maintain a list of field names.
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  values: FieldValues,
): string[] {
  const orphans: string[] = []
  for (const [field, message] of Object.entries(serverFieldErrors(error))) {
    // `items.0.quantity` belongs to `items`; react-hook-form and the API
    // spell a nested path the same way, so only the root needs checking.
    const root = field.split('.')[0]
    if (root && root in values) {
      setError(field as Path<T>, { type: 'server', message })
    } else {
      orphans.push(message)
    }
  }
  return orphans
}

/**
 * The same thing for a form holding its errors in `useState`.
 *
 * `clear` is called on submit rather than on change: a server error is about
 * what was sent, so it should survive editing until something is sent again.
 */
export function useServerFieldErrors(): {
  fieldErrors: Record<string, string>
  showErrorsFrom: (error: unknown) => void
  clearFieldErrors: () => void
} {
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  return {
    fieldErrors,
    showErrorsFrom: useCallback((error: unknown) => setFieldErrors(serverFieldErrors(error)), []),
    clearFieldErrors: useCallback(() => setFieldErrors({}), []),
  }
}

/**
 * The same, for a form whose submit lives in its parent.
 *
 * The wizard and the talent dashboard own the mutation while the form owns
 * the fields, so the error has to travel back down: the parent passes the
 * last failure as a prop and this puts it on the inputs. Keyed on the error
 * object, which is a fresh one per failed submission — so re-submitting and
 * failing the same way re-applies the messages rather than looking inert.
 *
 * Messages with no matching field are dropped here rather than shown twice:
 * every one of these parents already toasts the envelope sentence.
 */
export function useApplyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  getValues: () => FieldValues,
): void {
  useEffect(() => {
    if (!error) return
    applyServerFieldErrors(error, setError, getValues())
  }, [error, setError, getValues])
}
