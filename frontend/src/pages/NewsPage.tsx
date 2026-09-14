import { Newspaper } from 'lucide-react'

import { EmptyState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/** A placeholder for the activities-and-news section named in the top nav —
 * the link works, and promises nothing about content yet. */
export function NewsPage() {
  const t = useT()
  useSeo({ title: `${t('news.title')} | ${t('app.name')}` })

  return (
    <div className="container-page py-16">
      <h1 className="mb-8 text-center text-2xl sm:text-3xl">{t('news.title')}</h1>
      <EmptyState
        icon={<Newspaper className="h-7 w-7" aria-hidden="true" />}
        title={t('home.comingSoon')}
        description={t('news.comingSoonBody')}
      />
    </div>
  )
}
