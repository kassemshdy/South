/**
 * Translation layer.
 *
 * No user-facing string is written in a component. Everything lives in
 * `locales/<locale>.json`, so adding a language is a translation task rather
 * than a code change.
 *
 * Keys are typed from the Arabic catalog, which is the source of truth: a typo
 * or a key missing from another language fails the build instead of rendering
 * a blank space in production.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import ar from '@/i18n/locales/ar.json'

export type TranslationKey = keyof typeof ar
export type Locale = 'ar' | 'en'

/**
 * English is fetched only by someone who reads the site in English.
 *
 * Both catalogs used to be in the main bundle -- some 150 KB of text before
 * compression, on every visit to an Arabic-first site, for a language most
 * visitors never switch to. Arabic stays in the bundle because it is the
 * default and the fallback; English arrives the first time it is chosen.
 */
type Catalog = Record<TranslationKey, string>
type EnglishCatalog = typeof import('@/i18n/locales/en.json')
/** An English catalog missing a key is still a compile error, as it was. */
const englishIsComplete: EnglishCatalog extends Catalog ? true : never = true
void englishIsComplete

const CATALOGS: Partial<Record<Locale, Catalog>> = { ar }

/** Resolves once `locale`'s catalog is available; immediate for Arabic. */
export function loadLocale(locale: Locale): Promise<void> {
  if (CATALOGS[locale]) return Promise.resolve()
  return import('@/i18n/locales/en.json').then((module) => {
    // TypeScript types a JSON import as the object itself; at runtime the
    // bundler hands back a module whose `default` is that object.
    const loaded = module as unknown as { default?: Catalog } & Catalog
    CATALOGS.en = loaded.default ?? loaded
  })
}

export const LOCALE_DIRECTION: Record<Locale, 'rtl' | 'ltr'> = { ar: 'rtl', en: 'ltr' }
export const DEFAULT_LOCALE: Locale = 'ar'

const STORAGE_KEY = 'south.locale'

export type TranslateParams = Record<string, string | number>

function interpolate(template: string, params?: TranslateParams): string {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = params[name]
    return value === undefined ? match : String(value)
  })
}

export function translate(
  locale: Locale,
  key: TranslationKey,
  params?: TranslateParams,
): string {
  const template = CATALOGS[locale]?.[key] ?? ar[key]
  if (template === undefined) {
    // Surfaced loudly in development; renders the key rather than an empty gap.
    if (import.meta.env.DEV) console.error(`[i18n] unknown key: ${key}`)
    return key
  }
  return interpolate(template, params)
}

interface I18nContextValue {
  locale: Locale
  dir: 'rtl' | 'ltr'
  t: (key: TranslationKey, params?: TranslateParams) => string
  setLocale: (locale: Locale) => void
}

const I18nContext = createContext<I18nContextValue | null>(null)

/**
 * The locale the site is currently rendering in.
 *
 * Exported because the API client needs it too, and reads it from here
 * rather than keeping its own copy: the language a request asks for has to
 * be the language on the screen. This is a plain function, not a hook, so a
 * non-React module can call it — and localStorage is the honest source,
 * because `setLocale` writes it on every change.
 */
export function activeLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'ar' || stored === 'en') return stored
  } catch {
    // Private browsing can throw on storage access; the default is fine.
  }
  return DEFAULT_LOCALE
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(activeLocale)

  // The document element carries language and direction, so RTL comes from one
  // place rather than being reapplied per component.
  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = LOCALE_DIRECTION[locale]
  }, [locale])

  const setLocale = useCallback((next: Locale) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Non-fatal: the choice simply will not survive a reload.
    }
    // Switch once the words are here, so the page never shows keys or a
    // half-translated screen while English is on its way. If it cannot be
    // fetched the page stays as it is, in Arabic.
    loadLocale(next).then(
      () => setLocaleState(next),
      () => undefined,
    )
  }, [])

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      dir: LOCALE_DIRECTION[locale],
      t: (key, params) => translate(locale, key, params),
      setLocale,
    }),
    [locale, setLocale],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n must be used within I18nProvider')
  return context
}

/** Convenience for components that only need the translate function. */
export function useT(): (key: TranslationKey, params?: TranslateParams) => string {
  return useI18n().t
}
