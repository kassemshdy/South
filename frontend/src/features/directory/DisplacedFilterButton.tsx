import { House } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'

/**
 * Narrows a directory to owners who chose to show they are displaced. Kept
 * in the URL (`?displaced=1`) like every other filter, so the list can be
 * shared; the server only ever matches owners who opted in.
 */
export function DisplacedFilterButton({
  active,
  onToggle,
}: {
  active: boolean
  onToggle: () => void
}) {
  const t = useT()
  return (
    <Button variant={active ? 'primary' : 'outline'} size="sm" aria-pressed={active} onClick={onToggle}>
      <House className="h-4 w-4" aria-hidden="true" />
      {t('displaced.filter')}
    </Button>
  )
}
