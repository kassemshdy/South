import { Star } from 'lucide-react'

import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

const SCALE = [1, 2, 3, 4, 5] as const

/** A rating shown as five stars, filled up to the (rounded) value. */
export function Stars({ value, className }: { value: number; className?: string }) {
  const t = useT()
  const filled = Math.round(value)
  return (
    <span
      role="img"
      aria-label={t('testimonials.starsOf', { count: value.toFixed(1).replace(/\.0$/, '') })}
      className={cn('inline-flex items-center gap-0.5', className)}
    >
      {SCALE.map((step) => (
        <Star
          key={step}
          className={cn(
            'h-4 w-4',
            step <= filled ? 'fill-wheat-500 text-wheat-500' : 'fill-transparent text-ink-300',
          )}
          aria-hidden="true"
        />
      ))}
    </span>
  )
}

/**
 * Choosing a rating: optional, so pressing the chosen star again clears it.
 * Radio buttons underneath, so it is reachable and announced as a choice of
 * one in five without any custom keyboard handling.
 */
export function StarInput({
  value,
  onChange,
  label,
}: {
  value: number | null
  onChange: (value: number | null) => void
  label: string
}) {
  const t = useT()
  return (
    <fieldset>
      <legend className="mb-1.5 block text-sm font-semibold text-ink-700">
        {label}
        <span className="ms-2 text-xs font-normal text-ink-300">{t('common.optional')}</span>
      </legend>
      <div className="flex items-center gap-1" dir="ltr">
        {SCALE.map((step) => (
          <label key={step} className="cursor-pointer rounded p-0.5 focus-within:ring-2 focus-within:ring-brand-500/40">
            <input
              type="radio"
              name="rating"
              value={step}
              checked={value === step}
              onChange={() => onChange(step)}
              onClick={() => {
                if (value === step) onChange(null)
              }}
              className="sr-only"
              aria-label={t('testimonials.starsOf', { count: String(step) })}
            />
            <Star
              className={cn(
                'h-7 w-7 transition-colors',
                value !== null && step <= value
                  ? 'fill-wheat-500 text-wheat-500'
                  : 'fill-transparent text-ink-300 hover:text-wheat-500',
              )}
              aria-hidden="true"
            />
          </label>
        ))}
      </div>
    </fieldset>
  )
}
