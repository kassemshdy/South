import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useI18n } from '@/i18n'
import type { PageMeta } from '@/types/api'

/**
 * Numbered pagination. The chevrons follow reading direction: in RTL
 * "previous" points right, in LTR it points left.
 */
export function Pagination({ meta, onChange }: { meta: PageMeta; onChange: (page: number) => void }) {
  const { t, dir } = useI18n()
  if (meta.total_pages <= 1) return null

  const pages = buildPageList(meta.page, meta.total_pages)
  const PreviousIcon = dir === 'rtl' ? ChevronRight : ChevronLeft
  const NextIcon = dir === 'rtl' ? ChevronLeft : ChevronRight

  return (
    <nav className="mt-10 flex items-center justify-center gap-1.5" aria-label={t('pagination.aria')}>
      <Button
        variant="outline"
        size="icon"
        onClick={() => onChange(meta.page - 1)}
        disabled={!meta.has_previous}
        aria-label={t('pagination.previous')}
      >
        <PreviousIcon className="h-5 w-5" aria-hidden="true" />
      </Button>

      {pages.map((page, index) =>
        page === null ? (
          <span key={`gap-${index}`} className="px-2 text-ink-300" aria-hidden="true">
            …
          </span>
        ) : (
          <Button
            key={page}
            variant={page === meta.page ? 'primary' : 'outline'}
            size="icon"
            onClick={() => onChange(page)}
            aria-current={page === meta.page ? 'page' : undefined}
            aria-label={t('pagination.page', { page })}
          >
            {page}
          </Button>
        ),
      )}

      <Button
        variant="outline"
        size="icon"
        onClick={() => onChange(meta.page + 1)}
        disabled={!meta.has_next}
        aria-label={t('pagination.next')}
      >
        <NextIcon className="h-5 w-5" aria-hidden="true" />
      </Button>
    </nav>
  )
}

/** Windowed page numbers with ellipses, e.g. 1 … 4 [5] 6 … 20. */
function buildPageList(current: number, total: number): (number | null)[] {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  const pages: (number | null)[] = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  if (start > 2) pages.push(null)
  for (let page = start; page <= end; page += 1) pages.push(page)
  if (end < total - 1) pages.push(null)
  pages.push(total)

  return pages
}
