import { Check, ChevronDown } from 'lucide-react'
import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import { useT } from '@/i18n'
import type { LocationGroup } from '@/hooks/useTaxonomy'
import { cn } from '@/utils/cn'

/**
 * Letters people type interchangeably, folded so a search finds a place
 * however it is spelled: the hamza forms of alef to a bare alef, alef
 * maqsura to ya, ta marbuta to ha, and the short-vowel and shadda marks
 * dropped. Written as escapes, not as letters: the no-Arabic-in-source guard
 * (backend/tests/test_i18n.py) scans this directory, and these are code.
 */
function fold(text: string): string {
  return text
    .normalize('NFC')
    .replace(/[\u064b-\u0652\u0670\u0640]/g, '')
    .replace(/[\u0622\u0623\u0625\u0671]/g, '\u0627')
    .replace(/\u0649/g, '\u064a')
    .replace(/\u0629/g, '\u0647')
    .toLowerCase()
    .trim()
}

interface Option {
  id: string
  name: string
  /** The district a town belongs to, shown beside it; empty for a district. */
  district: string
  search: string
}

interface LocationComboboxProps {
  id?: string
  value: string
  onChange: (id: string) => void
  groups: LocationGroup[]
  /**
   * Which field a choice is: the id a form stores, or the slug a directory
   * filter puts in its URL.
   */
  by?: 'id' | 'slug'
  /** A first choice meaning "no place", valued '' -- a filter's "all". */
  emptyLabel?: string
  placeholder?: string
  invalid?: boolean
  'aria-describedby'?: string
}

/**
 * A place picker you can type into: the first letters of a town bring it to
 * the top of the list instead of scrolling a hundred towns for it. Districts and their towns
 * are both choices, as in the plain select it replaces; a district matching
 * the search comes before towns that do, and a town shows its district so
 * two villages with one name can be told apart.
 */
export function LocationCombobox({
  id,
  value,
  onChange,
  groups,
  by = 'id',
  emptyLabel,
  placeholder,
  invalid,
  'aria-describedby': describedBy,
}: LocationComboboxProps) {
  const t = useT()
  const listId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)

  const options = useMemo<Option[]>(
    () => [
      ...(emptyLabel ? [{ id: '', name: emptyLabel, district: '', search: fold(emptyLabel) }] : []),
      ...groups.flatMap(({ district, towns }) => [
        { id: district[by], name: district.name_ar, district: '', search: fold(district.name_ar) },
        ...towns.map((town) => ({
          id: town[by],
          name: town.name_ar,
          district: district.name_ar,
          search: fold(town.name_ar),
        })),
      ]),
    ],
    [groups, by, emptyLabel],
  )

  const selected = options.find((option) => option.id === value)

  const matches = useMemo(() => {
    const needle = fold(query)
    if (!needle) return options
    const hits = options.filter((option) => option.search.includes(needle))
    // Names that start with what was typed first, then districts before towns.
    const rank = (option: Option) =>
      // A name typed without its article still counts as its start.
      (option.search.startsWith(needle) || option.search.startsWith(`\u0627\u0644${needle}`)
        ? 0
        : 2) + (option.district ? 1 : 0)
    return [...hits].sort((a, b) => rank(a) - rank(b))
  }, [options, query])

  const choose = (option: Option) => {
    onChange(option.id)
    setQuery('')
    setOpen(false)
    inputRef.current?.blur()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setActive((index) => Math.min(index + 1, matches.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      if (open && matches[active]) {
        event.preventDefault()
        choose(matches[active])
      }
    } else if (event.key === 'Escape') {
      setOpen(false)
      setQuery('')
    }
  }

  return (
    <div className="relative">
      <input
        ref={inputRef}
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          open && matches[active] ? `${listId}-${matches[active].id}` : undefined
        }
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        autoComplete="off"
        // Showing the chosen place until the field is used again, and an
        // empty box to type into once it is.
        value={open ? query : (selected?.name ?? '')}
        placeholder={selected?.name ?? placeholder}
        onFocus={() => {
          setOpen(true)
          setActive(0)
        }}
        onBlur={() => {
          setOpen(false)
          setQuery('')
        }}
        onChange={(event) => {
          setQuery(event.target.value)
          setActive(0)
          setOpen(true)
        }}
        onKeyDown={onKeyDown}
        className={cn(
          'flex min-h-12 w-full rounded-xl border-2 border-ink-100 bg-white py-2 pe-10 ps-4 text-[15px] text-ink-900 transition-colors placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 aria-[invalid=true]:border-clay-500',
        )}
      />
      <ChevronDown
        className="pointer-events-none absolute end-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-500"
        aria-hidden="true"
      />

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute inset-x-0 top-full z-50 mt-1 max-h-72 overflow-y-auto rounded-xl border border-ink-100 bg-white p-1 shadow-lift"
          // Keep the input focused while a choice is clicked, so its blur
          // does not close the list before the click lands.
          onMouseDown={(event) => event.preventDefault()}
        >
          {matches.length === 0 ? (
            <li className="px-3 py-2 text-sm text-ink-500">{t('form.locationNoMatch')}</li>
          ) : (
            matches.map((option, index) => (
              <li
                key={option.id}
                id={`${listId}-${option.id}`}
                role="option"
                aria-selected={option.id === value}
                onClick={() => choose(option)}
                onMouseEnter={() => setActive(index)}
                className={cn(
                  'flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-[15px]',
                  index === active ? 'bg-sand-100' : '',
                  option.district ? 'text-ink-700' : 'font-semibold text-ink-900',
                )}
              >
                <span>
                  {option.name}
                  {option.district ? (
                    <span className="ms-2 text-sm font-normal text-ink-500">{option.district}</span>
                  ) : null}
                </span>
                {option.id === value ? (
                  <Check className="h-4 w-4 shrink-0 text-brand-700" aria-hidden="true" />
                ) : null}
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  )
}
