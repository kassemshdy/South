import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { forwardRef, type ButtonHTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

const buttonVariants = cva(
  // Generous min-height: these are tapped on phones, not clicked with a mouse.
  'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:pointer-events-none disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        primary: 'bg-clay-500 text-white shadow-card hover:bg-clay-600 active:bg-clay-700',
        secondary: 'bg-olive-500 text-white shadow-card hover:bg-olive-600',
        outline: 'border-2 border-ink-100 bg-white text-ink-900 hover:border-clay-300 hover:bg-sand-50',
        ghost: 'text-ink-700 hover:bg-sand-100 hover:text-ink-900',
        danger: 'bg-clay-700 text-white hover:bg-clay-800',
        whatsapp: 'bg-[#25D366] text-white shadow-card hover:bg-[#1da851]',
      },
      size: {
        sm: 'min-h-9 px-3 text-sm',
        md: 'min-h-11 px-5 text-[15px]',
        lg: 'min-h-13 px-7 text-base sm:text-lg',
        icon: 'h-11 w-11',
      },
      block: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'primary', size: 'md', block: false },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, block, asChild = false, loading = false, children, disabled, ...props },
  ref,
) {
  const Component = asChild ? Slot : 'button'
  return (
    <Component
      ref={ref}
      className={cn(buttonVariants({ variant, size, block }), className)}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span>{children}</span>
        </>
      ) : (
        children
      )}
    </Component>
  )
})
