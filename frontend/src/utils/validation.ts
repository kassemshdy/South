/**
 * Zod schema builders for the forms.
 *
 * Each builder takes the translate function so messages come from the catalog
 * rather than being hardcoded. These are a convenience for immediate feedback,
 * never the security boundary: the API re-validates everything.
 */

import { z } from 'zod'

import type { TranslationKey } from '@/i18n'

type Translate = (key: TranslationKey, params?: Record<string, string | number>) => string

/**
 * Arabic-Indic (U+0660..U+0669) and Extended Arabic-Indic (U+06F0..U+06F9)
 * digits, which Arabic keyboards produce. Written as code points rather than
 * glyphs: this is the algorithm, not translatable text.
 */
const ARABIC_INDIC_DIGITS = /[\u0660-\u0669\u06F0-\u06F9]/g

function toAsciiDigits(value: string): string {
  return value.replace(ARABIC_INDIC_DIGITS, (digit) => {
    const code = digit.charCodeAt(0)
    const base = code >= 0x06f0 ? 0x06f0 : 0x0660
    return String(code - base)
  })
}

export function isLebanesePhone(value: string): boolean {
  const digits = toAsciiDigits(value)
    .replace(/[^\d]/g, '')
    .replace(/^00/, '')
    .replace(/^961/, '')
    .replace(/^0/, '')
  return /^[1-9]\d{6,7}$/.test(digits)
}

/** Loose on purpose: the server is the judge of an address, not this. */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isUsableUrl(value: string): boolean {
  try {
    const url = new URL(value.includes('://') ? value : `https://${value}`)
    return ['http:', 'https:'].includes(url.protocol) && url.hostname.includes('.')
  } catch {
    return false
  }
}

/** Accepts 03 123 456, 71234567, +961…, 00961… and Arabic-Indic digits. */
export const lebanesePhone = (t: Translate) =>
  z
    .string()
    .trim()
    .min(1, t('validation.phoneRequired'))
    .refine(isLebanesePhone, t('validation.phoneInvalid'))

export const optionalPhone = (t: Translate) =>
  z
    .string()
    .trim()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || isLebanesePhone(value), t('validation.phoneInvalid'))

export const optionalUrl = (t: Translate) =>
  z
    .string()
    .trim()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || isUsableUrl(value), t('validation.urlInvalid'))

/**
 * The one sign-in form.
 *
 * A single box that takes either a phone number or an email address, because
 * the form has one box: an owner knows the number their account is keyed by,
 * an administrator knows their address, and asking which of the two somebody
 * is before they have proved anything is a question with no useful answer.
 *
 * The "@" picks which rule applies — no Lebanese number contains one — and
 * this is a typing aid only. The API answers every failed sign-in with the
 * same sentence whatever was typed, deliberately, so nothing here decides
 * anything.
 */
export const signInSchema = (t: Translate) =>
  z.object({
    identifier: z
      .string()
      .trim()
      .min(1, t('validation.identifierRequired'))
      .refine(
        (value) => (value.includes('@') ? EMAIL_PATTERN.test(value) : isLebanesePhone(value)),
        t('validation.identifierInvalid'),
      ),
    password: z.string().min(1, t('validation.passwordRequired')),
  })

/**
 * Choosing a password to replace the one an administrator issued.
 *
 * The confirmation field is checked here rather than server-side because it
 * is a typing aid, not a rule: the API takes one password and has nothing to
 * compare a second against.
 */
export const changePasswordSchema = (t: Translate) =>
  z
    .object({
      current_password: z.string().min(1, t('validation.passwordRequired')),
      new_password: z.string().min(8, t('validation.passwordShort')),
      confirm_password: z.string().min(1, t('validation.passwordRequired')),
    })
    .refine((values) => values.new_password === values.confirm_password, {
      path: ['confirm_password'],
      message: t('validation.passwordMismatch'),
    })

/**
 * The one field a registration form adds to the listing form it wraps: the
 * number that becomes the account's login, which is also where the
 * credentials are sent. Required, unlike the listing's published phone.
 */
export const loginPhoneSchema = (t: Translate) => z.object({ login_phone: lebanesePhone(t) })

export const adminLoginSchema = (t: Translate) =>
  z.object({
    email: z
      .string()
      .trim()
      .min(1, t('validation.emailRequired'))
      .email(t('validation.emailInvalid')),
    password: z.string().min(8, t('validation.passwordShort')),
  })

/**
 * `otherCategoryId` is passed in rather than hardcoded: the "Other" category
 * is a seeded row with a real (env-dependent) id, not a fixed constant, so the
 * free-text requirement can only be wired up once the category list has
 * loaded.
 */
export const businessBasicsSchema = (t: Translate, otherCategoryId?: string) =>
  z
    .object({
      name: z
        .string()
        .trim()
        .min(2, t('validation.nameRequired'))
        .max(160, t('validation.nameTooLong')),
      short_description: z
        .string()
        .trim()
        .max(300, t('validation.shortDescriptionTooLong'))
        .optional()
        .or(z.literal('')),
      description: z
        .string()
        .trim()
        .max(5000, t('validation.descriptionTooLong'))
        .optional()
        .or(z.literal('')),
      category_id: z.string().min(1, t('validation.categoryRequired')),
      custom_category_text: z.string().trim().max(120).optional().or(z.literal('')),

      // Producer detail — optional, and published like the rest of this step.
      institution_name: z.string().trim().max(200).optional().or(z.literal('')),
      founding_date: z
        .string()
        .trim()
        .optional()
        .or(z.literal(''))
        .refine(
          (value) => !value || !Number.isNaN(Date.parse(value)),
          t('validation.foundingDateInvalid'),
        ),
      production_nature: z.string().trim().max(5000).optional().or(z.literal('')),
      years_of_experience: z
        .string()
        .trim()
        .optional()
        .or(z.literal(''))
        .refine(
          (value) => !value || (/^\d+$/.test(value) && Number(value) <= 100),
          t('validation.yearsOfExperienceInvalid'),
        ),
      // Who is listing this -- a reviewer's question, and optional like the
      // rest of this step; the empty string is "not chosen", mapped to null
      // on submit alongside every other optional field here.
      owner_relation: z.enum(['OWNER', 'MANAGER', 'WORKER']).optional().or(z.literal('')),
      // Always one or the other; the form starts it from the door chosen.
      goods_origin: z.enum(['LOCAL', 'IMPORTED']),

      phone: optionalPhone(t),
      whatsapp: optionalPhone(t),
      email: z.string().trim().email(t('validation.emailInvalid')).optional().or(z.literal('')),
      website: optionalUrl(t),
    })
    .superRefine((values, ctx) => {
      if (
        otherCategoryId &&
        values.category_id === otherCategoryId &&
        !values.custom_category_text
      ) {
        ctx.addIssue({
          code: 'custom',
          path: ['custom_category_text'],
          message: t('validation.customCategoryRequired'),
        })
      }
    })

export const businessLocationSchema = (t: Translate) =>
  z.object({
    location_id: z.string().min(1, t('validation.locationRequired')),
    address_text: z
      .string()
      .trim()
      .max(400, t('validation.addressTooLong'))
      .optional()
      .or(z.literal('')),
    maps_url: optionalUrl(t),
  })

export const socialLinksSchema = (t: Translate) =>
  z.object({
    instagram: optionalUrl(t),
    facebook: optionalUrl(t),
    tiktok: optionalUrl(t),
    youtube: optionalUrl(t),
    whatsapp_url: optionalUrl(t),
    website: optionalUrl(t),
    // The introduction video, which is a link here and an id once stored.
    // Shape is checked server-side, where the parser that extracts the id
    // lives; this only keeps an obviously-not-a-URL out of the request.
    video_url: optionalUrl(t),
  })

export const itemSchema = (t: Translate) =>
  z.object({
    title: z
      .string()
      .trim()
      .min(1, t('validation.itemNameRequired'))
      .max(160, t('validation.nameTooLong')),
    description: z.string().trim().max(2000).optional().or(z.literal('')),
    price: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine(
        (value) => !value || (/^\d+(\.\d{1,2})?$/.test(value) && Number(value) >= 0),
        t('validation.priceInvalid'),
      ),
    currency: z.enum(['USD', 'LBP']),
    is_available: z.boolean(),
    good_type: z.string().trim().max(160).optional().or(z.literal('')),
    brand_name: z.string().trim().max(160).optional().or(z.literal('')),
    ingredients: z.string().trim().max(2000).optional().or(z.literal('')),
    manufactured_at: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || !Number.isNaN(Date.parse(value)), t('validation.dateInvalid')),
    expiry_date: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || !Number.isNaN(Date.parse(value)), t('validation.dateInvalid')),
    net_weight: z.string().trim().max(80).optional().or(z.literal('')),
    external_link: optionalUrl(t),
    goods_origin: z.enum(['LOCAL', 'IMPORTED']),
  })

/**
 * `otherSkillId` mirrors `businessBasicsSchema`'s `otherCategoryId`: the
 * "Other" skill is a seeded row with a real id, so the free-text requirement
 * can only be wired up once the skill list has loaded.
 */
export const talentSchema = (t: Translate, otherSkillId?: string) =>
  z
    .object({
      display_name: z
        .string()
        .trim()
        .min(2, t('validation.nameRequired'))
        .max(160, t('validation.nameTooLong')),
      bio: z.string().trim().max(5000, t('validation.descriptionTooLong')).optional().or(z.literal('')),
      years_experience: z
        .string()
        .trim()
        .optional()
        .or(z.literal(''))
        .refine(
          (value) => !value || (/^\d{1,2}$/.test(value) && Number(value) <= 70),
          t('validation.yearsInvalid'),
        ),
      skill_id: z.string().min(1, t('validation.skillRequired')),
      custom_skill_text: z.string().trim().max(120).optional().or(z.literal('')),
      location_id: z.string().min(1, t('validation.locationRequired')),
      phone: optionalPhone(t),
      whatsapp: optionalPhone(t),
      email: z.string().trim().email(t('validation.emailInvalid')).optional().or(z.literal('')),
      website: optionalUrl(t),
      // An introduction video. A link here, an id once the server stores it.
      video_url: optionalUrl(t),
      // One level below the chosen skill, in the person's own words.
      skill_specialty: z.string().trim().max(160).optional().or(z.literal('')),
      // Empty means no preference, which is a valid answer.
      preferred_contact: z
        .enum(['PHONE', 'WHATSAPP', 'EMAIL', 'WEBSITE'])
        .optional()
        .or(z.literal('')),

      // Published professional detail.
      highest_degree: z.string().trim().max(160).optional().or(z.literal('')),
      specialization: z.string().trim().max(160).optional().or(z.literal('')),
      university: z.string().trim().max(200).optional().or(z.literal('')),
      education_years: z
        .string()
        .trim()
        .optional()
        .or(z.literal(''))
        .refine(
          (value) => !value || (/^\d{1,2}$/.test(value) && Number(value) <= 30),
          t('validation.yearsInvalid'),
        ),
      graduation_date: z
        .string()
        .trim()
        .optional()
        .or(z.literal(''))
        .refine((value) => !value || !Number.isNaN(Date.parse(value)), t('validation.dateInvalid')),
      study_focus: z.string().trim().max(2000).optional().or(z.literal('')),
      experience: z.string().trim().max(5000).optional().or(z.literal('')),
      professional_training: z.string().trim().max(2000).optional().or(z.literal('')),
      skills_text: z.string().trim().max(2000).optional().or(z.literal('')),
      services_offered: z.string().trim().max(2000).optional().or(z.literal('')),
      hobbies: z.string().trim().max(1000).optional().or(z.literal('')),
      employment_type: z.enum(['FULL_TIME', 'PART_TIME']).optional().or(z.literal('')),
      remote_capable: z.boolean(),
      languages: z
        .array(
          z.object({
            name: z.string().trim().min(1, t('validation.languageNameRequired')).max(80),
            proficiency: z.enum(['BASIC', 'GOOD', 'FLUENT', 'NATIVE']),
          }),
        )
        .max(20)
        .optional(),
    })
    .superRefine((values, ctx) => {
      if (otherSkillId && values.skill_id === otherSkillId && !values.custom_skill_text) {
        ctx.addIssue({
          code: 'custom',
          path: ['custom_skill_text'],
          message: t('validation.customSkillRequired'),
        })
      }
    })

export const accountSchema = (t: Translate) =>
  z.object({
    display_name: z.string().trim().max(120, t('validation.displayNameLong')),
    personal_phone_number: optionalPhone(t),

    // Identity — one copy per account, shared by every listing it owns.
    full_name: z.string().trim().max(200).optional().or(z.literal('')),
    birth_year: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine(
        (value) => !value || (/^\d{4}$/.test(value) && Number(value) >= 1900 && Number(value) <= 2100),
        t('validation.birthYearInvalid'),
      ),
    gender: z.enum(['MALE', 'FEMALE']).optional().or(z.literal('')),
    marital_status: z
      .enum(['SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED'])
      .optional()
      .or(z.literal('')),
    registration_place: z.string().trim().max(160).optional().or(z.literal('')),
    residence_place: z.string().trim().max(200).optional().or(z.literal('')),
  })

export const rejectSchema = (t: Translate) =>
  z.object({
    reason: z.string().trim().min(5, t('validation.rejectReasonShort')).max(1000),
  })

export const feedbackTicketSchema = (t: Translate) =>
  z.object({
    title: z.string().trim().min(2, t('validation.titleRequired')).max(200),
    description: z.string().trim().max(5000).optional().or(z.literal('')),
    priority: z.enum(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
  })

export const commentSchema = (t: Translate) =>
  z.object({
    body: z.string().trim().min(1, t('validation.commentRequired')).max(4000),
  })

export type BusinessBasicsValues = z.infer<ReturnType<typeof businessBasicsSchema>>
export type BusinessLocationValues = z.infer<ReturnType<typeof businessLocationSchema>>
export type SocialLinksValues = z.infer<ReturnType<typeof socialLinksSchema>>
export type ItemValues = z.infer<ReturnType<typeof itemSchema>>
export type AccountValues = z.infer<ReturnType<typeof accountSchema>>
export type TalentValues = z.infer<ReturnType<typeof talentSchema>>
export type FeedbackTicketValues = z.infer<ReturnType<typeof feedbackTicketSchema>>
export type CommentValues = z.infer<ReturnType<typeof commentSchema>>
