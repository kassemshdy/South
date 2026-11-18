import { LayoutGrid } from 'lucide-react'

import { CategoryIcon } from '@/features/home/categoryIcon'
import { useT } from '@/i18n'
import type { Category } from '@/types/api'
import { cn } from '@/utils/cn'

/**
 * The products page's categories as a row of icons (the owners' request,
 * 18 Nov 2026): one tap filters, a second tap on the chosen one clears it.
 * Only categories with products a visitor can see, the fullest first.
 */
export function CategoryIconFilter({
  categories,
  value,
  onChange,
}: {
  categories: Category[]
  value: string
  onChange: (slug: string) => void
}) {
  const t = useT()
  const shown = categories
    .filter((category) => category.item_count > 0 || category.slug === value)
    .sort((a, b) => b.item_count - a.item_count)
  if (shown.length === 0) return null
  const chip = (active: boolean) =>
    cn(
      'flex h-full w-24 shrink-0 flex-col items-center gap-1.5 rounded-2xl border px-2 py-3 text-center transition-colors',
      active
        ? 'border-brand-700 bg-brand-50 text-brand-800'
        : 'border-ink-100 bg-white text-ink-700 hover:border-brand-300',
    )
  return (
    <nav aria-label={t('directory.category')} className="-mx-4 mb-6 px-4">
      <ul className="flex gap-3 overflow-x-auto pb-2">
        <li>
          <button type="button" className={chip(!value)} aria-pressed={!value} onClick={() => onChange('')}>
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <LayoutGrid className="h-6 w-6" aria-hidden="true" />
            </span>
            <span className="line-clamp-2 text-xs font-semibold leading-snug">
              {t('directory.allCategories')}
            </span>
          </button>
        </li>
        {shown.map((category) => {
          const active = category.slug === value
          return (
            <li key={category.id}>
              <button
                type="button"
                className={chip(active)}
                aria-pressed={active}
                onClick={() => onChange(active ? '' : category.slug)}
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <CategoryIcon name={category.icon} className="h-6 w-6" />
                </span>
                <span className="line-clamp-2 text-xs font-semibold leading-snug" dir="auto">
                  {category.name_ar}
                </span>
                <span className="ltr-nums text-[11px] text-ink-500">{category.item_count}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
