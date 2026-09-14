import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, ImagePlus, Trash2, X } from 'lucide-react'
import { useRef, useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminArticle, ArticleSection } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/format'

type Filter = ArticleSection | 'ALL'

const FILTERS: { value: Filter; labelKey: TranslationKey }[] = [
  { value: 'ALL', labelKey: 'admin.articleFilterAll' },
  { value: 'BLOG', labelKey: 'blog.title' },
  { value: 'NEWS', labelKey: 'news.title' },
]

interface FormState {
  section: ArticleSection
  title: string
  body: string
}

const EMPTY_FORM: FormState = { section: 'BLOG', title: '', body: '' }

/**
 * Admin-only content management for the two "coming soon" pages in the top
 * nav. Nothing here is owner- or visitor-submitted, so there is no
 * moderation queue to work through — just write, publish and, when needed,
 * unpublish or delete.
 */
export function AdminArticlesPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<Filter>('ALL')
  const [editingId, setEditingId] = useState<string | 'new' | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const articles = useQuery({
    queryKey: queryKeys.adminArticles(filter),
    queryFn: () => adminApi.articles(filter === 'ALL' ? undefined : filter),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'articles'] })
    void queryClient.invalidateQueries({ queryKey: ['articles'] })
    void queryClient.invalidateQueries({ queryKey: ['article'] })
  }

  const handleError = (error: unknown, fallback: string) =>
    toast.error(fallback, error instanceof ApiError ? error.message : undefined)

  const startEditing = (article: AdminArticle) => {
    setEditingId(article.id)
    setForm({ section: article.section, title: article.title, body: article.body })
  }

  const create = useMutation({
    mutationFn: (payload: FormState) => adminApi.createArticle(payload),
    onSuccess: () => {
      setEditingId(null)
      setForm(EMPTY_FORM)
      toast.success(t('admin.articleAdded'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.articleSaveFailed')),
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: FormState }) =>
      adminApi.updateArticle(id, payload),
    onSuccess: () => {
      setEditingId(null)
      toast.success(t('admin.articleSaved'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.articleSaveFailed')),
  })

  const togglePublish = useMutation({
    mutationFn: (article: AdminArticle) =>
      article.is_published
        ? adminApi.unpublishArticle(article.id)
        : adminApi.publishArticle(article.id),
    onSuccess: () => invalidate(),
    onError: (error) => handleError(error, t('admin.articleSaveFailed')),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteArticle(id),
    onSuccess: () => {
      setConfirmingId(null)
      toast.success(t('admin.articleDeleted'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.articleDeleteFailed')),
  })

  const uploadCover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => adminApi.uploadArticleCover(id, file),
    onSuccess: () => invalidate(),
    onError: (error) => handleError(error, t('admin.articleCoverUploadFailed')),
    onSettled: () => setUploadingId(null),
  })

  const removeCover = useMutation({
    mutationFn: (id: string) => adminApi.deleteArticleCover(id),
    onSuccess: () => invalidate(),
    onError: (error) => handleError(error, t('admin.articleCoverUploadFailed')),
  })

  const renderForm = (onSubmit: () => void, pending: boolean) => (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
      className="space-y-3"
    >
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-ink-700" id="article-section">
          {t('admin.articleSectionLabel')}
        </label>
        <Select
          value={form.section}
          onValueChange={(value) => setForm((prev) => ({ ...prev, section: value as ArticleSection }))}
        >
          <SelectTrigger aria-labelledby="article-section" className="max-w-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="BLOG">{t('blog.title')}</SelectItem>
            <SelectItem value="NEWS">{t('news.title')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <label htmlFor="article-title" className="mb-1.5 block text-sm font-semibold text-ink-700">
          {t('admin.articleTitleLabel')}
        </label>
        <Input
          id="article-title"
          value={form.title}
          onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
          dir="auto"
          required
        />
      </div>

      <div>
        <label htmlFor="article-body" className="mb-1.5 block text-sm font-semibold text-ink-700">
          {t('admin.articleBodyLabel')}
        </label>
        <Textarea
          id="article-body"
          value={form.body}
          onChange={(event) => setForm((prev) => ({ ...prev, body: event.target.value }))}
          dir="auto"
          rows={6}
          required
        />
      </div>

      <div className="flex gap-2">
        <Button type="submit" loading={pending} disabled={form.title.trim().length < 3}>
          {t('common.save')}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setEditingId(null)
            setForm(EMPTY_FORM)
          }}
        >
          {t('common.cancel')}
        </Button>
      </div>
    </form>
  )

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.articlesHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.articlesSubtitle')}</p>
      </header>

      {editingId === 'new' ? (
        <Card>
          <CardBody>{renderForm(() => create.mutate(form), create.isPending)}</CardBody>
        </Card>
      ) : (
        <Button
          onClick={() => {
            setEditingId('new')
            setForm(EMPTY_FORM)
          }}
        >
          {t('admin.newArticle')}
        </Button>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((option) => {
          const isActive = filter === option.value
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              aria-pressed={isActive}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
                isActive
                  ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                  : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
              )}
            >
              {t(option.labelKey)}
            </button>
          )
        })}
      </div>

      {articles.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : articles.isError ? (
        <ErrorState error={articles.error} onRetry={() => void articles.refetch()} />
      ) : articles.data && articles.data.length > 0 ? (
        <ul className="space-y-3">
          {articles.data.map((article) => (
            <li key={article.id}>
              <Card>
                <CardBody className="space-y-3">
                  {editingId === article.id ? (
                    renderForm(
                      () => update.mutate({ id: article.id, payload: form }),
                      update.isPending,
                    )
                  ) : (
                    <>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-sand-100">
                            {article.cover_url ? (
                              <img
                                src={article.cover_url}
                                alt=""
                                className="h-full w-full object-cover"
                              />
                            ) : null}
                          </div>
                          <div>
                            <p className="font-semibold text-ink-900" dir="auto">
                              {article.title}
                            </p>
                            <p className="mt-0.5 text-sm text-ink-500">
                              {t(article.section === 'BLOG' ? 'blog.title' : 'news.title')}
                              {article.published_at ? ` · ${formatDate(article.published_at, locale)}` : ''}
                            </p>
                          </div>
                        </div>
                        <Badge
                          className={
                            article.is_published
                              ? 'bg-olive-100 text-olive-700'
                              : 'bg-sand-100 text-clay-700'
                          }
                        >
                          {t(article.is_published ? 'admin.articlePublished' : 'admin.articleDraft')}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={() => startEditing(article)}>
                          {t('common.edit')}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={togglePublish.isPending}
                          onClick={() => togglePublish.mutate(article)}
                        >
                          {article.is_published ? (
                            <EyeOff className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <Eye className="h-4 w-4" aria-hidden="true" />
                          )}
                          {t(article.is_published ? 'admin.articleUnpublish' : 'admin.articlePublish')}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={uploadingId === article.id && uploadCover.isPending}
                          onClick={() => {
                            setUploadingId(article.id)
                            fileInput.current?.click()
                          }}
                        >
                          <ImagePlus className="h-4 w-4" aria-hidden="true" />
                          {t('admin.articleCover')}
                        </Button>
                        {article.cover_url ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeCover.mutate(article.id)}
                          >
                            {t('admin.articleRemoveCover')}
                          </Button>
                        ) : null}

                        <div className="ms-auto">
                          {confirmingId === article.id ? (
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-ink-500">
                                {t('admin.articleDeleteConfirm')}
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setConfirmingId(null)}
                                disabled={remove.isPending}
                              >
                                <X className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                loading={remove.isPending}
                                onClick={() => remove.mutate(article.id)}
                              >
                                {t('common.delete')}
                              </Button>
                            </div>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-clay-600"
                              onClick={() => setConfirmingId(article.id)}
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                              {t('common.delete')}
                            </Button>
                          )}
                        </div>
                      </div>
                    </>
                  )}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('admin.articlesEmpty')} />
      )}

      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          if (file && uploadingId) uploadCover.mutate({ id: uploadingId, file })
        }}
      />
    </div>
  )
}
