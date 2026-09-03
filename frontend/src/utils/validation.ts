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

function isLebanesePhone(value: string): boolean {
  const digits = toAsciiDigits(value)
    .replace(/[^\d]/g, '')
    .replace(/^00/, '')
    .replace(/^961/, '')
    .replace(/^0/, '')
  return /^[1-9]\d{6,7}$/.test(digits)
}

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

export const otpSchema = (t: Translate) =>
  z.object({
    code: z
      .string()
      .trim()
      .regex(/^\d{4,8}$/, t('validation.otpDigits')),
  })

export const phoneSchema = (t: Translate) => z.object({ phone_number: lebanesePhone(t) })

export const adminLoginSchema = (t: Translate) =>
  z.object({
    email: z
      .string()
      .trim()
      .min(1, t('validation.emailRequired'))
      .email(t('validation.emailInvalid')),
    password: z.string().min(8, t('validation.passwordShort')),
  })

export const businessBasicsSchema = (t: Translate) =>
  z.object({
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
    phone: optionalPhone(t),
    whatsapp: optionalPhone(t),
    email: z.string().trim().email(t('validation.emailInvalid')).optional().or(z.literal('')),
    website: optionalUrl(t),
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
  })

export const rejectSchema = (t: Translate) =>
  z.object({
    reason: z.string().trim().min(5, t('validation.rejectReasonShort')).max(1000),
  })

export type BusinessBasicsValues = z.infer<ReturnType<typeof businessBasicsSchema>>
export type BusinessLocationValues = z.infer<ReturnType<typeof businessLocationSchema>>
export type SocialLinksValues = z.infer<ReturnType<typeof socialLinksSchema>>
export type ItemValues = z.infer<ReturnType<typeof itemSchema>>
