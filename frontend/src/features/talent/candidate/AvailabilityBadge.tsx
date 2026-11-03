import { Badge } from '@/components/ui/Badge'
import { AVAILABILITY_KEYS, AVAILABILITY_TONES } from '@/features/talent/candidate/labels'
import { useT } from '@/i18n'
import type { TalentAvailability } from '@/types/api'
import { cn } from '@/utils/cn'

export function AvailabilityBadge({
  availability,
  className,
}: {
  availability: TalentAvailability | undefined
  className?: string
}) {
  const t = useT()
  if (!availability) return null
  return (
    <Badge className={cn(AVAILABILITY_TONES[availability], className)}>
      {t(AVAILABILITY_KEYS[availability])}
    </Badge>
  )
}
