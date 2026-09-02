import { cn } from '@/utils/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} aria-hidden="true" />
}

/** Placeholder matching the real business card's shape to avoid layout shift. */
export function BusinessCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card">
      <Skeleton className="h-36 w-full rounded-none" />
      <div className="space-y-3 p-5">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    </div>
  )
}
