import { useQuery } from '@tanstack/react-query'
import type { ComponentType, SVGProps } from 'react'

import { BusinessCardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { ArticleCard } from '@/features/articles/ArticleCard'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { publicArticleApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ArticleSection } from '@/types/api'

interface Props {
  section: ArticleSection
  titleKey: TranslationKey
  emptyDescriptionKey: TranslationKey
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

/**
 * The list behind `/blog` and `/news`. Both pages are the same shape — a
 * heading and a grid of published articles for one section — so the shape
 * lives here once, and each page just names its section, its copy and its
 * icon. Falls back to the original "coming soon" empty state when a section
 * has nothing published yet, rather than showing a bare empty grid.
 */
export function ArticleSectionPage({ section, titleKey, emptyDescriptionKey, icon: Icon }: Props) {
  const t = useT()
  useSeo({ title: `${t(titleKey)} | ${t('app.name')}` })

  const results = useQuery({
    queryKey: queryKeys.articles(section),
    queryFn: () => publicArticleApi.list(section),
  })

  return (
    <div className="container-page py-16">
      <h1 className="mb-8 text-center text-2xl sm:text-3xl">{t(titleKey)}</h1>

      {results.isLoading ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <BusinessCardSkeleton key={index} />
          ))}
        </div>
      ) : results.isError ? (
        <ErrorState error={results.error} onRetry={() => void results.refetch()} />
      ) : results.data && results.data.length > 0 ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {results.data.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Icon className="h-7 w-7" aria-hidden="true" />}
          title={t('home.comingSoon')}
          description={t(emptyDescriptionKey)}
        />
      )}
    </div>
  )
}
