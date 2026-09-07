/**
 * Enum → translation-key maps for the account holder's identity.
 *
 * Typed maps rather than template-built keys, so a missing translation is a
 * compile error like everywhere else in the app. Identity belongs to the
 * account, so these are shared by the account form and by the admin review
 * card — one map means the two cannot label the same value differently.
 */

import type { TranslationKey } from '@/i18n'
import type { Gender, MaritalStatus } from '@/types/api'

export const GENDERS = ['MALE', 'FEMALE'] as const
export const MARITAL_STATUSES = ['SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED'] as const

export const GENDER_KEYS: Record<Gender, TranslationKey> = {
  MALE: 'identity.genderMale',
  FEMALE: 'identity.genderFemale',
}

export const MARITAL_STATUS_KEYS: Record<MaritalStatus, TranslationKey> = {
  SINGLE: 'identity.maritalSingle',
  MARRIED: 'identity.maritalMarried',
  DIVORCED: 'identity.maritalDivorced',
  WIDOWED: 'identity.maritalWidowed',
}
