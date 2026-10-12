/**
 * Enum → translation-key map for a talent profile's languages.
 *
 * A typed map rather than template-built keys, so a missing translation is a
 * compile error like everywhere else in the app. It lives here rather than in
 * the form because the public profile and the admin review page render the
 * same enum and must label it identically.
 */

import type { TranslationKey } from '@/i18n'
import type { EmploymentType, LanguageProficiency, WorkMode } from '@/types/api'

export const LANGUAGE_PROFICIENCIES = ['BASIC', 'GOOD', 'FLUENT', 'NATIVE'] as const

export const PROFICIENCY_KEYS: Record<LanguageProficiency, TranslationKey> = {
  BASIC: 'talentForm.levelBasic',
  GOOD: 'talentForm.levelGood',
  FLUENT: 'talentForm.levelFluent',
  NATIVE: 'talentForm.levelNative',
}

export const EMPLOYMENT_TYPE_KEYS: Record<EmploymentType, TranslationKey> = {
  FULL_TIME: 'talentForm.employmentTypeFullTime',
  PART_TIME: 'talentForm.employmentTypePartTime',
}

/** Remotely, in person, or both, in the order the form offers them. */
export const WORK_MODES = ['ON_SITE', 'REMOTE', 'BOTH'] as const satisfies readonly WorkMode[]

export const WORK_MODE_KEYS: Record<WorkMode, TranslationKey> = {
  REMOTE: 'talent.workModeRemote',
  ON_SITE: 'talent.workModeOnSite',
  BOTH: 'talent.workModeBoth',
}
