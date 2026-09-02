/** Arabic-aware formatting helpers shared across the UI. */

import type { BusinessStatus, Currency, SocialPlatform } from '@/types/api'

export const STATUS_LABELS: Record<BusinessStatus, string> = {
  DRAFT: 'مسودة',
  PENDING_REVIEW: 'قيد المراجعة',
  APPROVED: 'مقبول',
  REJECTED: 'يحتاج إلى تعديل',
  SUSPENDED: 'موقوف',
}

export const STATUS_TONES: Record<BusinessStatus, string> = {
  DRAFT: 'bg-ink-100 text-ink-700',
  PENDING_REVIEW: 'bg-sand-200 text-clay-800',
  APPROVED: 'bg-olive-100 text-olive-700',
  REJECTED: 'bg-clay-100 text-clay-700',
  SUSPENDED: 'bg-ink-100 text-ink-700',
}

export const PLATFORM_LABELS: Record<SocialPlatform, string> = {
  INSTAGRAM: 'إنستغرام',
  FACEBOOK: 'فيسبوك',
  TIKTOK: 'تيك توك',
  YOUTUBE: 'يوتيوب',
  WHATSAPP: 'واتساب',
  WEBSITE: 'الموقع الإلكتروني',
}

const CURRENCY_LABELS: Record<Currency, string> = { USD: '$', LBP: 'ل.ل.' }

/**
 * Format a price. Prices arrive as decimal strings so they are never subject to
 * float rounding; only the display is localized.
 *
 * Deliberately formatted with Latin digits and a period decimal separator:
 * that is how prices are written on Lebanese menus and price lists. The
 * ar-LB locale would render ١٫٥٠, and ar-LB-u-nu-latn would render 1,50 —
 * neither is what a shopper here expects to see next to a dollar sign.
 */
export function formatPrice(price: string | null, currency: Currency = 'USD'): string | null {
  if (price === null || price === '') return null
  const value = Number(price)
  if (Number.isNaN(value)) return null

  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: currency === 'LBP' ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value)

  return currency === 'USD'
    ? `${CURRENCY_LABELS.USD}${formatted}`
    : `${formatted} ${CURRENCY_LABELS.LBP}`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  // Levantine Arabic month names (أيلول rather than سبتمبر) with Latin digits.
  return new Intl.DateTimeFormat('ar-LB-u-nu-latn', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(iso))
}

export function formatRelativeDate(iso: string | null): string {
  if (!iso) return '—'
  const diffDays = Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (diffDays < 1) return 'اليوم'
  if (diffDays === 1) return 'أمس'
  if (diffDays < 30) return `قبل ${diffDays} يوماً`
  return formatDate(iso)
}

/** wa.me requires digits only; our stored numbers are E.164 with a leading +. */
export function whatsappHref(number: string | null, message?: string): string | null {
  if (!number) return null
  const digits = number.replace(/[^\d]/g, '')
  if (!digits) return null
  const suffix = message ? `?text=${encodeURIComponent(message)}` : ''
  return `https://wa.me/${digits}${suffix}`
}

export function telHref(number: string | null): string | null {
  return number ? `tel:${number.replace(/\s/g, '')}` : null
}

/** Display a phone number left-to-right even inside RTL text. */
export function displayPhone(number: string | null): string {
  return number ?? ''
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((part) => part[0] ?? '').join('')
}
