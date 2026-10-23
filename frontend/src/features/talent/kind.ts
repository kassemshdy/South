import type { TalentKind } from '@/types/api'

/**
 * The kind a visitor picked on the offer page, carried in `?kind=` to the
 * application form or the dashboard, so the form opens with it chosen.
 * Anything else is no choice at all, and the form asks.
 */
export function kindFromQuery(value: string | null): TalentKind | undefined {
  return value === 'SERVICE' || value === 'JOB_SEEKER' ? value : undefined
}

/** The directory a profile of this kind is listed in. */
export function directoryPath(kind: TalentKind | undefined): string {
  return kind === 'JOB_SEEKER' ? '/jobs' : '/services'
}
