import { BookOpen } from 'lucide-react'

import { ArticleSectionPage } from '@/features/articles/ArticleSectionPage'

/** Professional tips, named in the top nav. Falls back to an empty state
 * until at least one is published. */
export function BlogPage() {
  return (
    <ArticleSectionPage
      section="BLOG"
      titleKey="blog.title"
      emptyDescriptionKey="blog.comingSoonBody"
      icon={BookOpen}
    />
  )
}
