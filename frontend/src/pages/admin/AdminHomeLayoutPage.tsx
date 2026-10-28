import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { PREVIEW_PARAM, PREVIEW_VALUE, PROPOSED_ORDER } from '@/features/home/layout'
import { useT, type TranslationKey } from '@/i18n'
import { adminApi, homeApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { HomeSection, HomeSectionId } from '@/types/api'

const LABELS: Record<HomeSectionId, TranslationKey> = {
  cover: 'admin.homeSectionCover',
  hero: 'admin.homeSectionHero',
  slogan: 'admin.homeSectionSlogan',
  search: 'admin.homeSectionSearch',
  categories: 'admin.homeSectionCategories',
  stories: 'admin.homeSectionStories',
  reels: 'admin.homeSectionReels',
  stats: 'admin.homeSectionStats',
  products: 'admin.homeSectionProducts',
  category_products: 'admin.homeSectionCategoryProducts',
  shops: 'admin.homeSectionShops',
  talents: 'admin.homeSectionTalents',
  news: 'admin.homeSectionNews',
  blog: 'admin.homeSectionBlog',
}

/**
 * The home page's sections, in order, each shown or hidden (the owners'
 * request, 27 Oct 2026). Moved with up/down buttons rather than dragging:
 * they work the same on a phone and with a keyboard.
 */
export function AdminHomeLayoutPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const layout = useQuery({ queryKey: queryKeys.homeLayout, queryFn: homeApi.layout })
  const [sections, setSections] = useState<HomeSection[]>([])

  useEffect(() => {
    if (layout.data) setSections(layout.data.sections)
  }, [layout.data])

  const save = useMutation({
    mutationFn: () => adminApi.saveHomeLayout({ sections }),
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.homeLayout, saved)
      toast.success(t('admin.correctionSaved'))
    },
    onError: () => toast.error(t('admin.correctionFailed')),
  })

  const move = (index: number, by: -1 | 1) => {
    const next = [...sections]
    const target = index + by
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target]!, next[index]!]
    setSections(next)
  }
  // The proposed page, as previewed: its sections in its order, shown, and
  // anything it leaves out kept below, hidden. Saved only by Save.
  const applyProposed = () => {
    const rest = sections.filter((s) => !PROPOSED_ORDER.includes(s.id))
    setSections([
      ...PROPOSED_ORDER.map((id) => ({ id, visible: true })),
      ...rest.map((s) => ({ ...s, visible: false })),
    ])
  }

  const toggle = (index: number) =>
    setSections(sections.map((s, i) => (i === index ? { ...s, visible: !s.visible } : s)))

  if (layout.isLoading) return <InlineSpinner />
  if (layout.isError) return <ErrorState error={layout.error} onRetry={() => void layout.refetch()} />

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.homeLayoutTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.homeLayoutHint')}</p>
      </header>
      <Card>
        <CardBody className="p-0">
          <ol className="divide-y divide-ink-100">
            {sections.map((section, index) => (
              <li key={section.id} className="flex items-center gap-3 px-4 py-3">
                <span className="ltr-nums w-6 text-center text-sm font-semibold text-ink-500">{index + 1}</span>
                <label className="flex flex-1 items-center gap-3">
                  <input
                    type="checkbox"
                    checked={section.visible}
                    onChange={() => toggle(index)}
                    className="h-5 w-5 accent-brand-700"
                  />
                  <span className={section.visible ? 'font-semibold text-ink-900' : 'text-ink-500 line-through'}>
                    {t(LABELS[section.id])}
                  </span>
                </label>
                <button
                  type="button"
                  aria-label={t('admin.moveUp')}
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                  className="flex h-10 w-10 items-center justify-center rounded-lg ring-1 ring-ink-100 hover:bg-sand-100 disabled:opacity-40"
                >
                  <ArrowUp className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={t('admin.moveDown')}
                  disabled={index === sections.length - 1}
                  onClick={() => move(index, 1)}
                  className="flex h-10 w-10 items-center justify-center rounded-lg ring-1 ring-ink-100 hover:bg-sand-100 disabled:opacity-40"
                >
                  <ArrowDown className="h-4 w-4" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ol>
        </CardBody>
      </Card>
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => save.mutate()} loading={save.isPending}>
          {t('common.save')}
        </Button>
        <Button variant="secondary" onClick={applyProposed}>
          {t('admin.homeLayoutApplyProposed')}
        </Button>
        <a
          href={`/?${PREVIEW_PARAM}=${PREVIEW_VALUE}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center rounded-xl px-4 py-2.5 font-semibold text-brand-700 hover:bg-sand-100"
        >
          {t('admin.homeLayoutPreview')}
        </a>
      </div>
    </div>
  )
}
