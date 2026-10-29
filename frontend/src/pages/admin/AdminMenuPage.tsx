import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { SITE_SECTIONS } from '@/components/layout/navigation'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { adminApi, menuApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { MenuItem } from '@/types/api'

const INPUT =
  'w-full rounded-lg border border-ink-100 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none'

/**
 * The site menu -- the header row, its drawer and the footer -- in order,
 * each item shown or hidden and, if wanted, renamed in either language (the
 * owners' request, 29 Oct 2026). An empty name keeps the site's own.
 */
export function AdminMenuPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const menu = useQuery({ queryKey: queryKeys.siteMenu, queryFn: menuApi.get })
  const [items, setItems] = useState<MenuItem[]>([])

  useEffect(() => {
    if (menu.data) setItems(menu.data.items)
  }, [menu.data])

  const save = useMutation({
    mutationFn: () => adminApi.saveMenu({ items }),
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.siteMenu, saved)
      toast.success(t('admin.correctionSaved'))
    },
    onError: () => toast.error(t('admin.correctionFailed')),
  })

  const update = (index: number, change: Partial<MenuItem>) =>
    setItems(items.map((item, i) => (i === index ? { ...item, ...change } : item)))
  const move = (index: number, by: -1 | 1) => {
    const next = [...items]
    const target = index + by
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target]!, next[index]!]
    setItems(next)
  }

  if (menu.isLoading) return <InlineSpinner />
  if (menu.isError) return <ErrorState error={menu.error} onRetry={() => void menu.refetch()} />

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.menuTitle')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.menuHint')}</p>
      </header>
      <Card>
        <CardBody className="p-0">
          <ol className="divide-y divide-ink-100">
            {items.map((item, index) => {
              const section = SITE_SECTIONS.find((entry) => entry.id === item.id)
              if (!section) return null
              const fallback = t(section.labelKey)
              return (
                <li key={item.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <span className="ltr-nums w-6 text-center text-sm font-semibold text-ink-500">
                    {index + 1}
                  </span>
                  <label className="flex min-w-32 flex-1 items-center gap-3">
                    <input
                      type="checkbox"
                      checked={item.visible}
                      onChange={() => update(index, { visible: !item.visible })}
                      className="h-5 w-5 accent-brand-700"
                    />
                    <span className={item.visible ? 'font-semibold text-ink-900' : 'text-ink-500 line-through'}>
                      {fallback}
                    </span>
                  </label>
                  <div className="grid w-full gap-2 sm:w-auto sm:flex-[2] sm:grid-cols-2">
                    <input
                      className={INPUT}
                      dir="rtl"
                      maxLength={40}
                      aria-label={t('admin.menuLabelAr')}
                      placeholder={t('admin.menuLabelAr')}
                      value={item.label_ar ?? ''}
                      onChange={(event) => update(index, { label_ar: event.target.value })}
                    />
                    <input
                      className={INPUT}
                      dir="ltr"
                      maxLength={40}
                      aria-label={t('admin.menuLabelEn')}
                      placeholder={t('admin.menuLabelEn')}
                      value={item.label_en ?? ''}
                      onChange={(event) => update(index, { label_en: event.target.value })}
                    />
                  </div>
                  <div className="flex gap-2">
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
                      disabled={index === items.length - 1}
                      onClick={() => move(index, 1)}
                      className="flex h-10 w-10 items-center justify-center rounded-lg ring-1 ring-ink-100 hover:bg-sand-100 disabled:opacity-40"
                    >
                      <ArrowDown className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              )
            })}
          </ol>
        </CardBody>
      </Card>
      <Button onClick={() => save.mutate()} loading={save.isPending}>
        {t('common.save')}
      </Button>
    </div>
  )
}
