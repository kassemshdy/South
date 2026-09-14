import { BookOpen } from 'lucide-react'

import { EmptyState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/** A placeholder for the professional-tips blog named in the top nav — the
 * link works, and promises nothing about content yet. */
export function BlogPage() {
  const t = useT()
  useSeo({ title: `${t('blog.title')} | ${t('app.name')}` })

  return (
    <div className="container-page py-16">
      <h1 className="mb-8 text-center text-2xl sm:text-3xl">{t('blog.title')}</h1>
      <EmptyState
        icon={<BookOpen className="h-7 w-7" aria-hidden="true" />}
        title={t('home.comingSoon')}
        description={t('blog.comingSoonBody')}
      />
    </div>
  )
}
