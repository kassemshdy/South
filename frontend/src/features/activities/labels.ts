import type { TranslationKey } from '@/i18n'
import type { Activity, ActivityKind } from '@/types/api'

/** What an announcement is, as its meta line names it. */
export const KIND_KEYS: Record<ActivityKind, TranslationKey> = {
  ACTIVITY: 'activitiesPage.kind.ACTIVITY',
  CONSULTATION: 'activitiesPage.kind.CONSULTATION',
  WORKSHOP: 'activitiesPage.kind.WORKSHOP',
  TRAINING: 'activitiesPage.kind.TRAINING',
}

/**
 * Finished: its end has passed, or its start when it gives no end -- the
 * same rule the API uses to take a finished activity out of the carousel.
 */
export function hasEnded(activity: Pick<Activity, 'starts_at' | 'ends_at'>): boolean {
  const end = activity.ends_at ?? activity.starts_at
  return end !== null && new Date(end).getTime() < Date.now()
}
