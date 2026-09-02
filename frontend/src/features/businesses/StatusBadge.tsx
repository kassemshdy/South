import { Badge } from '@/components/ui/Badge'
import type { BusinessStatus } from '@/types/api'
import { STATUS_LABELS, STATUS_TONES } from '@/utils/format'
import { cn } from '@/utils/cn'

export function StatusBadge({ status, className }: { status: BusinessStatus; className?: string }) {
  return (
    <Badge className={cn(STATUS_TONES[status], className)}>{STATUS_LABELS[status]}</Badge>
  )
}
