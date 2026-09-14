import { Newspaper } from 'lucide-react'

import { ArticleSectionPage } from '@/features/articles/ArticleSectionPage'

/** Activities and news, named in the top nav. Falls back to an empty state
 * until at least one is published. */
export function NewsPage() {
  return (
    <ArticleSectionPage
      section="NEWS"
      titleKey="news.title"
      emptyDescriptionKey="news.comingSoonBody"
      icon={Newspaper}
    />
  )
}
