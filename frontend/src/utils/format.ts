/**
 * Formatting helpers.
 *
 * These deliberately take a `t` function rather than importing the catalog:
 * formatting is locale-dependent, and passing the translator keeps these
 * functions pure and testable.
 */

import type { TranslationKey } from '@/i18n'
import type { BusinessStatus, Currency, FeedbackPriority, FeedbackStatus, SocialPlatform } from '@/types/api'

export const STATUS_KEYS: Record<BusinessStatus, TranslationKey> = {
  DRAFT: 'status.DRAFT',
  PENDING_REVIEW: 'status.PENDING_REVIEW',
  APPROVED: 'status.APPROVED',
  REJECTED: 'status.REJECTED',
  SUSPENDED: 'status.SUSPENDED',
}

export const STATUS_TONES: Record<BusinessStatus, string> = {
  DRAFT: 'bg-ink-100 text-ink-700',
  PENDING_REVIEW: 'bg-sand-200 text-clay-800',
  APPROVED: 'bg-olive-100 text-olive-700',
  REJECTED: 'bg-clay-100 text-clay-700',
  SUSPENDED: 'bg-ink-100 text-ink-700',
}

export const FEEDBACK_STATUS_KEYS: Record<FeedbackStatus, TranslationKey> = {
  BACKLOG: 'feedback.status.BACKLOG',
  TODO: 'feedback.status.TODO',
  IN_PROGRESS: 'feedback.status.IN_PROGRESS',
  DONE: 'feedback.status.DONE',
}

export const FEEDBACK_PRIORITY_KEYS: Record<FeedbackPriority, TranslationKey> = {
  LOW: 'feedback.priority.LOW',
  MEDIUM: 'feedback.priority.MEDIUM',
  HIGH: 'feedback.priority.HIGH',
  URGENT: 'feedback.priority.URGENT',
}

export const PLATFORM_KEYS: Record<SocialPlatform, TranslationKey> = {
  INSTAGRAM: 'platform.INSTAGRAM',
  FACEBOOK: 'platform.FACEBOOK',
  TIKTOK: 'platform.TIKTOK',
  YOUTUBE: 'platform.YOUTUBE',
  WHATSAPP: 'platform.WHATSAPP',
  WEBSITE: 'platform.WEBSITE',
}

const CURRENCY_SUFFIX: Record<Currency, string> = { USD: '$', LBP: 'LBP' }

/**
 * Format a price. Prices arrive as decimal strings so they are never subject to
 * float rounding; only the display is localized.
 *
 * Deliberately formatted with Latin digits and a period decimal separator:
 * that is how prices are written on Lebanese menus and price lists, in both
 * languages.
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
    ? `${CURRENCY_SUFFIX.USD}${formatted}`
    : `${formatted} ${CURRENCY_SUFFIX.LBP}`
}

/** Levantine Arabic month names with Latin digits; standard English elsewhere. */
export function formatDate(iso: string | null, locale: string): string {
  if (!iso) return '—'
  const tag = locale === 'ar' ? 'ar-LB-u-nu-latn' : 'en-GB'
  return new Intl.DateTimeFormat(tag, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(iso))
}

type Translate = (key: TranslationKey, params?: Record<string, string | number>) => string

export function formatRelativeDate(iso: string | null, locale: string, t: Translate): string {
  if (!iso) return '—'
  const diffDays = Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (diffDays < 1) return t('date.today')
  if (diffDays === 1) return t('date.yesterday')
  if (diffDays < 30) return t('date.daysAgo', { days: diffDays })
  return formatDate(iso, locale)
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
