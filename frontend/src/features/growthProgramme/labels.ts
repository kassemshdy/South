import type { TranslationKey } from '@/i18n'
import type { GrowthStage } from '@/types/api'

export const GROWTH_STAGE_KEYS: Record<GrowthStage, TranslationKey> = {
  CONTACTED: 'growthProgramme.stage.CONTACTED',
  CONTENT: 'growthProgramme.stage.CONTENT',
  LISTING: 'growthProgramme.stage.LISTING',
  SHOPIFY: 'growthProgramme.stage.SHOPIFY',
  ADS: 'growthProgramme.stage.ADS',
}

/** "1,200 → 1,500 (+300)", or a dash when there is no number. */
export function change(before: number | null, now: number | null, locale: string): string {
  const fmt = (value: number) => value.toLocaleString(locale === 'ar' ? 'ar-LB' : 'en')
  if (now == null) return '—'
  if (before == null) return fmt(now)
  const delta = now - before
  const sign = delta > 0 ? '+' : ''
  return `${fmt(before)} → ${fmt(now)} (${sign}${fmt(delta)})`
}
