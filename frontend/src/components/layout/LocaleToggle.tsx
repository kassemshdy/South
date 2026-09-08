import { Languages } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useI18n, type Locale, type TranslationKey } from '@/i18n'

/**
 * The control that made the English catalog reachable.
 *
 * Both catalogs have been complete and kept in lockstep by the build for a
 * while, but nothing in the app ever called `setLocale` — so every English
 * string we maintained was unreachable to a visitor. This is that missing
 * control, not a translation feature.
 *
 * It shows the language you would switch *to*, written in that language — an
 * endonym, the way every language picker does it. That matters most in the one
 * moment it has to work: someone who switched by accident and cannot read the
 * language they landed in still recognises the name of their own. A translated
 * label ("Arabic") would fail exactly that person, so the endonym is the same
 * string in both catalogs and is deliberately never translated.
 */

const NEXT_LOCALE: Record<Locale, Locale> = { ar: 'en', en: 'ar' }

const ENDONYM_KEYS: Record<Locale, TranslationKey> = {
  ar: 'nav.localeArabic',
  en: 'nav.localeEnglish',
}

export function LocaleToggle({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n()
  const next = NEXT_LOCALE[locale]
  const label = t(ENDONYM_KEYS[next])

  return (
    <Button
      type="button"
      variant="ghost"
      size={compact ? 'icon' : 'sm'}
      onClick={() => setLocale(next)}
      // The visible label is the target language's own name, so the accessible
      // name has to supply the verb — otherwise a screen reader announces a
      // bare language name with no indication that this switches anything.
      aria-label={t('nav.switchLanguage', { language: label })}
      title={t('nav.switchLanguage', { language: label })}
    >
      <Languages className="h-5 w-5 shrink-0" aria-hidden="true" />
      {compact ? null : <span>{label}</span>}
    </Button>
  )
}
