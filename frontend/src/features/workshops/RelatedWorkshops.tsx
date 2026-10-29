import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { WorkshopCard } from '@/features/workshops/WorkshopCard'
import { useT } from '@/i18n'
import { workshopApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

const SHOWN = 3

/**
 * Upcoming workshops about what a page is about: the category and town of a
 * product, or of a blog article. A workshop that names neither is about
 * everything, and an online one is open wherever the visitor is. Nothing at
 * all when none is coming up.
 */
export function RelatedWorkshops({
  category,
  location,
  className,
}: {
  category?: string | null
  location?: string | null
  className?: string
}) {
  const t = useT()
  const query = {
    ...(category ? { category } : {}),
    ...(location ? { location } : {}),
    limit: SHOWN,
  }
  const workshops = useQuery({
    queryKey: queryKeys.workshops(query),
    queryFn: () => workshopApi.list(query),
  })
  const items = workshops.data ?? []
  if (items.length === 0) return null
  return (
    <section className={className ?? 'mt-12 border-t border-ink-100 pt-8'} aria-labelledby="related-workshops">
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h2 id="related-workshops" className="text-xl sm:text-2xl">
          {t('workshops.related')}
        </h2>
        <Link to="/workshops" className="shrink-0 text-sm font-semibold text-brand-700 hover:underline">
          {t('workshops.viewAll')}
        </Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((workshop) => (
          <WorkshopCard key={workshop.id} workshop={workshop} />
        ))}
      </div>
    </section>
  )
}
