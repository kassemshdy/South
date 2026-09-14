import { Newspaper } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useI18n } from '@/i18n'
import type { Article } from '@/types/api'
import { formatDate } from '@/utils/format'

export function ArticleCard({ article }: { article: Article }) {
  const { locale } = useI18n()
  const detailUrl = `/articles/${encodeURIComponent(article.slug)}`

  return (
    <article className="group flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift">
      <Link to={detailUrl} className="block" tabIndex={-1} aria-hidden="true">
        <div className="relative h-36 overflow-hidden bg-sand-100">
          {article.cover_url ? (
            <img
              src={article.cover_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sand-500">
              <Newspaper className="h-10 w-10" aria-hidden="true" />
            </div>
          )}
        </div>
      </Link>

      <div className="flex flex-1 flex-col p-5" dir="auto">
        {article.published_at ? (
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
            {formatDate(article.published_at, locale)}
          </p>
        ) : null}

        <h3 className="text-lg font-bold text-ink-900">
          <Link to={detailUrl} className="transition-colors hover:text-brand-700">
            {article.title}
          </Link>
        </h3>

        <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-ink-500">{article.body}</p>
      </div>
    </article>
  )
}
