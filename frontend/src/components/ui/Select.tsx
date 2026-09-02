import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import { forwardRef } from 'react'

import { cn } from '@/utils/cn'

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export const SelectTrigger = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> & { invalid?: boolean }
>(function SelectTrigger({ className, children, invalid, ...props }, ref) {
  return (
    <SelectPrimitive.Trigger
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'flex min-h-12 w-full items-center justify-between gap-2 rounded-xl border-2 border-ink-100 bg-white px-4 py-2 text-[15px] text-ink-900 transition-colors focus:border-clay-400 focus:outline-none focus:ring-2 focus:ring-clay-500/20 data-[placeholder]:text-ink-300 aria-[invalid=true]:border-clay-500',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="h-4 w-4 shrink-0 text-ink-500" aria-hidden="true" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
})

export const SelectContent = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(function SelectContent({ className, children, position = 'popper', ...props }, ref) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        ref={ref}
        position={position}
        className={cn(
          'z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-ink-100 bg-white shadow-lift',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
})

export const SelectItem = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(function SelectItem({ className, children, ...props }, ref) {
  return (
    <SelectPrimitive.Item
      ref={ref}
      className={cn(
        // ps-*/pe-* rather than pl-*/pr-* so the checkmark sits on the correct
        // side in RTL without a second stylesheet.
        'relative flex cursor-pointer select-none items-center rounded-lg py-2.5 pe-8 ps-3 text-[15px] outline-none data-[disabled]:pointer-events-none data-[highlighted]:bg-sand-100 data-[disabled]:opacity-50',
        className,
      )}
      {...props}
    >
      <span className="absolute end-2 flex h-4 w-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="h-4 w-4 text-clay-500" aria-hidden="true" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
})
