import { Badge } from '@/components/ui/Badge'
import { useT } from '@/i18n'
import type { BusinessStatus } from '@/types/api'
import { STATUS_KEYS, STATUS_TONES } from '@/utils/format'
import { cn } from '@/utils/cn'

export function StatusBadge({ status, className }: { status: BusinessStatus; className?: string }) {
  const t = useT()
  return <Badge className={cn(STATUS_TONES[status], className)}>{t(STATUS_KEYS[status])}</Badge>
}
