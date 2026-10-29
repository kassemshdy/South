import { House } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

/**
 * "Displaced from <place>", on a listing whose owner chose to show it.
 *
 * The place arrives only when the owner ticked the box on their account page
 * (the API sends null otherwise), so this renders nothing by default.
 */
export function DisplacedBadge({ place, className }: { place?: string | null; className?: string }) {
  const t = useT()
  if (!place) return null
  return (
    <Badge className={cn('bg-clay-50 text-clay-700', className)} dir="auto">
      <House className="h-3.5 w-3.5" aria-hidden="true" />
      {t('displaced.badge', { place })}
    </Badge>
  )
}
