/**
 * Enum → translation-key map for a talent profile's languages.
 *
 * A typed map rather than template-built keys, so a missing translation is a
 * compile error like everywhere else in the app. It lives here rather than in
 * the form because the public profile and the admin review page render the
 * same enum and must label it identically.
 */

import type { TranslationKey } from '@/i18n'
import type { LanguageProficiency } from '@/types/api'

export const LANGUAGE_PROFICIENCIES = ['BASIC', 'GOOD', 'FLUENT', 'NATIVE'] as const

export const PROFICIENCY_KEYS: Record<LanguageProficiency, TranslationKey> = {
  BASIC: 'talentForm.levelBasic',
  GOOD: 'talentForm.levelGood',
  FLUENT: 'talentForm.levelFluent',
  NATIVE: 'talentForm.levelNative',
}
