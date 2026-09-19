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

/**
 * The switch itself, without a control around it.
 *
 * Shared so the header's «more» menu offers the same language, named the same
 * way, as the button below `lg` — the endonym rule above is worth exactly one
 * copy, and a second hand-written mapping is how the two would drift.
 */
export function useLocaleSwitch(): {
  label: string
  action: string
  switchLocale: () => void
} {
  const { locale, setLocale, t } = useI18n()
  const next = NEXT_LOCALE[locale]
  const label = t(ENDONYM_KEYS[next])

  return {
    label,
    action: t('nav.switchLanguage', { language: label }),
    switchLocale: () => setLocale(next),
  }
}

export function LocaleToggle({ compact = false }: { compact?: boolean }) {
  const { label, action, switchLocale } = useLocaleSwitch()

  return (
    <Button
      type="button"
      variant="ghost"
      size={compact ? 'icon' : 'sm'}
      onClick={switchLocale}
      // The visible label is the target language's own name, so the accessible
      // name has to supply the verb — otherwise a screen reader announces a
      // bare language name with no indication that this switches anything.
      aria-label={action}
      title={action}
    >
      <Languages className="h-5 w-5 shrink-0" aria-hidden="true" />
      {compact ? null : <span>{label}</span>}
    </Button>
  )
}
