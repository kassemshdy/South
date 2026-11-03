/**
 * Enum → translation-key maps for the candidate directory, typed so a
 * missing translation is a compile error.
 */

import type { TranslationKey } from '@/i18n'
import type {
  EducationLevel,
  ExperienceBand,
  LanguageProficiency,
  TalentAvailability,
  TalentWorkType,
} from '@/types/api'

export const EXPERIENCE_BANDS = ['0-1', '2-4', '5-9', '10+'] as const satisfies readonly ExperienceBand[]

export const EXPERIENCE_KEYS: Record<ExperienceBand, TranslationKey> = {
  '0-1': 'candidate.experience.0-1',
  '2-4': 'candidate.experience.2-4',
  '5-9': 'candidate.experience.5-9',
  '10+': 'candidate.experience.10+',
}

export const EDUCATION_LEVELS = [
  'SECONDARY_VOCATIONAL',
  'UNIVERSITY',
  'POSTGRADUATE',
] as const satisfies readonly EducationLevel[]

export const EDUCATION_KEYS: Record<EducationLevel, TranslationKey> = {
  SECONDARY_VOCATIONAL: 'candidate.education.SECONDARY_VOCATIONAL',
  UNIVERSITY: 'candidate.education.UNIVERSITY',
  POSTGRADUATE: 'candidate.education.POSTGRADUATE',
}

export const WORK_TYPES = [
  'FULL_TIME',
  'PART_TIME',
  'REMOTE',
  'TRAINING',
] as const satisfies readonly TalentWorkType[]

export const WORK_TYPE_KEYS: Record<TalentWorkType, TranslationKey> = {
  FULL_TIME: 'candidate.workType.FULL_TIME',
  PART_TIME: 'candidate.workType.PART_TIME',
  REMOTE: 'candidate.workType.REMOTE',
  TRAINING: 'candidate.workType.TRAINING',
}

export const AVAILABILITY_KEYS: Record<TalentAvailability, TranslationKey> = {
  NOW: 'candidate.availability.NOW',
  WITHIN_MONTH: 'candidate.availability.WITHIN_MONTH',
  EMPLOYED_OPEN: 'candidate.availability.EMPLOYED_OPEN',
}

/** Green, amber, grey: ready now, soon, open to an offer. */
export const AVAILABILITY_TONES: Record<TalentAvailability, string> = {
  NOW: 'bg-olive-100 text-olive-800',
  WITHIN_MONTH: 'bg-wheat-100 text-wheat-700',
  EMPLOYED_OPEN: 'bg-ink-100 text-ink-700',
}

export const LEVEL_KEYS: Record<LanguageProficiency, TranslationKey> = {
  NATIVE: 'candidate.level.NATIVE',
  FLUENT: 'candidate.level.FLUENT',
  GOOD: 'candidate.level.GOOD',
  BASIC: 'candidate.level.BASIC',
}

export function experienceFrom(value: string | null): ExperienceBand | undefined {
  return EXPERIENCE_BANDS.find((band) => band === value)
}

export function educationFrom(value: string | null): EducationLevel | undefined {
  return EDUCATION_LEVELS.find((level) => level === value)
}

export function workTypeFrom(value: string | null): TalentWorkType | undefined {
  return WORK_TYPES.find((type) => type === value)
}
