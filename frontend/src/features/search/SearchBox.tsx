import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { FolderTree, Package, Search, Store, UserRound } from 'lucide-react'
import { useEffect, useId, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { useT, type TranslationKey } from '@/i18n'
import { searchApi } from '@/services/api/endpoints'
import type { SearchSuggestion } from '@/types/api'
import { cn } from '@/utils/cn'

/** Fewer letters than the server's own minimum suggest nothing. */
const MIN_LENGTH = 2
const DEBOUNCE_MS = 200

const GROUP_KEYS: Record<SearchSuggestion['kind'], TranslationKey> = {
  category: 'search.groupCategories',
  product: 'search.groupProducts',
  shop: 'search.groupShops',
  service: 'search.groupServices',
}

const ICONS = { category: FolderTree, product: Package, shop: Store, service: UserRound }

function hrefOf(suggestion: SearchSuggestion): string {
  const slug = encodeURIComponent(suggestion.slug)
  switch (suggestion.kind) {
    case 'category':
      return `/products?category=${slug}`
    case 'product':
      return `/product/${slug}`
    case 'shop':
      return `/business/${slug}`
    case 'service':
      return `/talent/${slug}`
  }
}

interface SearchBoxProps {
  /** What the box opens with, and follows when the page's query changes. */
  value?: string
  /** Searching for the typed text. Unset, it searches the products page. */
  onSearch?: (query: string) => void
  /** The label and placeholder; the products search by default. */
  label?: string
  /** `band` on the home page's coloured strip, `page` on a directory. */
  appearance?: 'band' | 'page'
  /** Extra controls after the search button, such as a filters toggle. */
  children?: ReactNode
}

/**
 * The site's search box, suggesting as someone types: categories,
 * products, shops and services, each opening its page, and a last row that
 * searches for exactly what was typed. A combobox in the ARIA
 * sense -- arrow keys move through the suggestions, Enter opens one,
 * Escape closes the list. The home page and the directories share it, so
 * suggesting works the same everywhere.
 */
export function SearchBox({
  value = '',
  onSearch,
  label,
  appearance = 'band',
  children,
}: SearchBoxProps = {}) {
  const t = useT()
  const navigate = useNavigate()
  const listId = useId()
  const [text, setText] = useState(value)
  const [term, setTerm] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)

  useEffect(() => {
    const timer = window.setTimeout(() => setTerm(text.trim()), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [text])

  const suggestions = useQuery({
    queryKey: ['search', 'suggest', term],
    queryFn: () => searchApi.suggest(term),
    enabled: term.length >= MIN_LENGTH,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  })
  const items = term.length >= MIN_LENGTH ? (suggestions.data ?? []) : []
  // The suggestions, then "search for what I typed".
  const rows = text.trim().length >= MIN_LENGTH ? items.length + 1 : 0
  const showing = open && rows > 0

  useEffect(() => setActive(-1), [term])
  useEffect(() => setText(value), [value])

  const searchFor = (typed: string) => {
    setOpen(false)
    const q = typed.trim()
    if (onSearch) onSearch(q)
    else navigate(q ? `/products?q=${encodeURIComponent(q)}` : '/products')
  }
  const go = (index: number) => {
    const suggestion = items[index]
    setOpen(false)
    if (suggestion) navigate(hrefOf(suggestion))
    else searchFor(text)
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (showing && active >= 0) go(active)
    else searchFor(text)
  }
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' && rows > 0) {
      event.preventDefault()
      setOpen(true)
      setActive((current) => (current + 1) % rows)
    } else if (event.key === 'ArrowUp' && rows > 0) {
      event.preventDefault()
      setOpen(true)
      setActive((current) => (current <= 0 ? rows - 1 : current - 1))
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const optionId = (index: number) => `${listId}-option-${index}`

  return (
    <form onSubmit={submit} className="relative flex gap-2" role="search">
      <label htmlFor={`${listId}-input`} className="sr-only">
        {label ?? t('products.searchLabel')}
      </label>
      <div className="relative min-w-0 flex-1">
        {appearance === 'page' ? (
          <Search
            className="pointer-events-none absolute inset-y-0 start-4 my-auto h-5 w-5 text-ink-300"
            aria-hidden="true"
          />
        ) : null}
        <input
          id={`${listId}-input`}
          type="search"
          role="combobox"
          aria-expanded={showing}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showing && active >= 0 ? optionId(active) : undefined}
          autoComplete="off"
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          // Long enough for a tap on a suggestion to land before the list goes.
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
          onKeyDown={onKeyDown}
          placeholder={label ?? t('products.searchLabel')}
          className={
            appearance === 'page'
              ? 'h-12 w-full rounded-xl border-2 border-ink-100 bg-white ps-12 pe-4 text-[15px] placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20'
              : 'h-12 w-full rounded-xl border-0 bg-white px-4 text-base text-ink-900 shadow-card focus:outline-none focus:ring-2 focus:ring-wheat-500'
          }
        />
      </div>
      <button
        type="submit"
        className={cn(
          'flex h-12 items-center gap-2 rounded-xl px-5 font-semibold text-white',
          appearance === 'page' ? 'bg-brand-700 hover:bg-brand-800' : 'bg-clay-500 hover:bg-clay-600',
        )}
      >
        <Search className="h-5 w-5" aria-hidden="true" />
        <span className="hidden sm:inline">{t('common.search')}</span>
      </button>
      {children}

      {showing ? (
        <ul
          id={listId}
          role="listbox"
          aria-label={t('search.suggestions')}
          className="absolute inset-x-0 top-full z-30 mt-2 max-h-[70dvh] overflow-y-auto rounded-2xl bg-white py-2 text-ink-900 shadow-lift ring-1 ring-ink-100"
        >
          {items.map((suggestion, index) => {
            const Icon = ICONS[suggestion.kind]
            const heading = index === 0 || items[index - 1]?.kind !== suggestion.kind
            return (
              <li key={`${suggestion.kind}-${suggestion.slug}`} role="presentation">
                {heading ? (
                  <p className="px-4 pb-1 pt-2 text-xs font-bold text-ink-500">
                    {t(GROUP_KEYS[suggestion.kind])}
                  </p>
                ) : null}
                <div
                  id={optionId(index)}
                  role="option"
                  aria-selected={active === index}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => go(index)}
                  onMouseEnter={() => setActive(index)}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 px-4 py-2',
                    active === index && 'bg-sand-100',
                  )}
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-sand-100 text-brand-700">
                    {suggestion.image_url ? (
                      <img src={suggestion.image_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    )}
                  </span>
                  <span className="flex min-w-0 flex-col" dir="auto">
                    <span className="truncate font-semibold">{suggestion.label}</span>
                    {suggestion.detail ? (
                      <span className="truncate text-xs text-ink-500">{suggestion.detail}</span>
                    ) : null}
                  </span>
                </div>
              </li>
            )
          })}
          <li role="presentation" className={cn(items.length > 0 && 'mt-1 border-t border-ink-100 pt-1')}>
            <div
              id={optionId(items.length)}
              role="option"
              aria-selected={active === items.length}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => go(items.length)}
              onMouseEnter={() => setActive(items.length)}
              className={cn(
                'flex cursor-pointer items-center gap-3 px-4 py-2.5 font-semibold text-brand-700',
                active === items.length && 'bg-sand-100',
              )}
            >
              <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">{t('search.searchFor', { term: text.trim() })}</span>
            </div>
          </li>
        </ul>
      ) : null}
    </form>
  )
}
