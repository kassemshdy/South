/**
 * Enum -> translation-key map for a business's `owner_relation`.
 *
 * Per business rather than per account -- see `OwnerRelation` in
 * `types/api.ts` -- so this lives beside the business form rather than in
 * `features/identity/labels.ts`. Reuses the form's own labels ("Owner",
 * "Manager", "Worker" read the same on a dropdown and on a review card), so
 * the two cannot drift into naming the same value differently.
 */

import type { TranslationKey } from '@/i18n'
import type { OwnerRelation } from '@/types/api'

export const OWNER_RELATION_KEYS: Record<OwnerRelation, TranslationKey> = {
  OWNER: 'form.ownerRelationOwner',
  MANAGER: 'form.ownerRelationManager',
  WORKER: 'form.ownerRelationWorker',
}
