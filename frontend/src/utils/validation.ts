/**
 * Zod schemas for the forms.
 *
 * These mirror the backend's Pydantic rules so users get immediate Arabic
 * feedback — but they are a convenience, never the security boundary: the API
 * re-validates everything.
 */

import { z } from 'zod'

/** Accepts 03 123 456, 71234567, +961..., 00961... and Arabic-Indic digits. */
export const lebanesePhone = z
  .string()
  .trim()
  .min(1, 'رقم الهاتف مطلوب')
  .transform((value) =>
    value.replace(/[٠-٩۰-۹]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'.indexOf(digit) % 10)),
  )
  .refine((value) => {
    const digits = value.replace(/[^\d]/g, '').replace(/^00/, '').replace(/^961/, '').replace(/^0/, '')
    return /^[1-9]\d{6,7}$/.test(digits)
  }, 'أدخل رقماً لبنانياً صحيحاً، مثل 03123456')

export const optionalPhone = z
  .string()
  .trim()
  .optional()
  .or(z.literal(''))
  .refine((value) => {
    if (!value) return true
    const digits = value.replace(/[^\d]/g, '').replace(/^00/, '').replace(/^961/, '').replace(/^0/, '')
    return /^[1-9]\d{6,7}$/.test(digits)
  }, 'أدخل رقماً لبنانياً صحيحاً، مثل 03123456')

export const optionalUrl = z
  .string()
  .trim()
  .optional()
  .or(z.literal(''))
  .refine((value) => {
    if (!value) return true
    try {
      const url = new URL(value.includes('://') ? value : `https://${value}`)
      return ['http:', 'https:'].includes(url.protocol) && url.hostname.includes('.')
    } catch {
      return false
    }
  }, 'أدخل رابطاً صحيحاً')

export const otpSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{4,8}$/, 'رمز التحقق يتكون من أرقام فقط'),
})

export const phoneSchema = z.object({ phone_number: lebanesePhone })

export const adminLoginSchema = z.object({
  email: z.string().trim().min(1, 'البريد الإلكتروني مطلوب').email('أدخل بريداً إلكترونياً صحيحاً'),
  password: z.string().min(8, 'كلمة المرور يجب ألا تقل عن 8 أحرف'),
})

export const businessBasicsSchema = z.object({
  name: z.string().trim().min(2, 'اسم النشاط مطلوب').max(160, 'الاسم طويل جداً'),
  short_description: z.string().trim().max(300, 'الوصف المختصر طويل جداً').optional().or(z.literal('')),
  description: z.string().trim().max(5000, 'الوصف طويل جداً').optional().or(z.literal('')),
  category_id: z.string().min(1, 'اختر تصنيفاً'),
  phone: optionalPhone,
  whatsapp: optionalPhone,
  email: z.string().trim().email('أدخل بريداً إلكترونياً صحيحاً').optional().or(z.literal('')),
  website: optionalUrl,
})

export const businessLocationSchema = z.object({
  location_id: z.string().min(1, 'اختر الموقع'),
  address_text: z.string().trim().max(400, 'العنوان طويل جداً').optional().or(z.literal('')),
  maps_url: optionalUrl,
})

export const socialLinksSchema = z.object({
  instagram: optionalUrl,
  facebook: optionalUrl,
  tiktok: optionalUrl,
  youtube: optionalUrl,
  whatsapp_url: optionalUrl,
  website: optionalUrl,
})

export const itemSchema = z.object({
  title: z.string().trim().min(1, 'اسم العنصر مطلوب').max(160, 'الاسم طويل جداً'),
  description: z.string().trim().max(2000).optional().or(z.literal('')),
  price: z
    .string()
    .trim()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || (/^\d+(\.\d{1,2})?$/.test(value) && Number(value) >= 0), 'أدخل سعراً صحيحاً'),
  currency: z.enum(['USD', 'LBP']),
  is_available: z.boolean(),
})

export const rejectSchema = z.object({
  reason: z.string().trim().min(5, 'يرجى كتابة سبب واضح للرفض (5 أحرف على الأقل)').max(1000),
})

export type BusinessBasicsValues = z.infer<typeof businessBasicsSchema>
export type BusinessLocationValues = z.infer<typeof businessLocationSchema>
export type SocialLinksValues = z.infer<typeof socialLinksSchema>
export type ItemValues = z.infer<typeof itemSchema>
