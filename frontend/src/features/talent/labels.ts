/**
 * Enum → translation-key maps for talent profile fields.
 *
 * Typed maps rather than template-built keys, so a missing translation is a
 * compile error like everywhere else in the app. They live here rather than in
 * the form because the public profile and the admin review page render the same
 * enums and must label them identically.
 */

import type { TranslationKey } from '@/i18n'
import type { Gender, LanguageProficiency, MaritalStatus } from '@/types/api'

export const LANGUAGE_PROFICIENCIES = ['BASIC', 'GOOD', 'FLUENT', 'NATIVE'] as const
export const MARITAL_STATUSES = ['SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED'] as const
export const GENDERS = ['MALE', 'FEMALE'] as const

export const PROFICIENCY_KEYS: Record<LanguageProficiency, TranslationKey> = {
  BASIC: 'talentForm.levelBasic',
  GOOD: 'talentForm.levelGood',
  FLUENT: 'talentForm.levelFluent',
  NATIVE: 'talentForm.levelNative',
}

export const MARITAL_STATUS_KEYS: Record<MaritalStatus, TranslationKey> = {
  SINGLE: 'talentForm.maritalSingle',
  MARRIED: 'talentForm.maritalMarried',
  DIVORCED: 'talentForm.maritalDivorced',
  WIDOWED: 'talentForm.maritalWidowed',
}

export const GENDER_KEYS: Record<Gender, TranslationKey> = {
  MALE: 'talentForm.genderMale',
  FEMALE: 'talentForm.genderFemale',
}
