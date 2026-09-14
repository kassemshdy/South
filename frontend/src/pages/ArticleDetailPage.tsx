import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, type TranslationKey } from '@/i18n'
import { publicArticleApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ArticleSection } from '@/types/api'
import { formatDate } from '@/utils/format'

const BACK: Record<ArticleSection, { to: string; labelKey: TranslationKey }> = {
  BLOG: { to: '/blog', labelKey: 'blog.title' },
  NEWS: { to: '/news', labelKey: 'news.title' },
}

export function ArticleDetailPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  const { t, locale } = useI18n()

  const result = useQuery({
    queryKey: queryKeys.article(slug),
    queryFn: () => publicArticleApi.bySlug(slug),
    enabled: Boolean(slug),
  })
  const article = result.data

  useSeo({
    title: article ? `${article.title} | ${t('app.name')}` : t('app.name'),
    description: article ? article.body.slice(0, 160) : undefined,
    image: article?.cover_url,
    canonicalPath: `/articles/${slug}`,
  })

  if (result.isLoading) {
    return (
      <div className="container-page max-w-3xl py-10">
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
  }

  if (result.isError || !article) {
    return (
      <div className="container-page max-w-3xl py-10">
        <ErrorState error={result.error} onRetry={() => void result.refetch()} />
      </div>
    )
  }

  const back = BACK[article.section]

  return (
    <div className="container-page max-w-3xl py-10">
      <Link
        to={back.to}
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700"
      >
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t(back.labelKey)}
      </Link>

      {article.cover_url ? (
        <img
          src={article.cover_url}
          alt=""
          className="mb-6 h-64 w-full rounded-2xl object-cover sm:h-80"
        />
      ) : null}

      <h1 className="text-2xl font-bold sm:text-3xl" dir="auto">
        {article.title}
      </h1>
      {article.published_at ? (
        <p className="mt-2 text-sm text-ink-500">{formatDate(article.published_at, locale)}</p>
      ) : null}

      <div className="mt-6 whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
        {article.body}
      </div>
    </div>
  )
}
