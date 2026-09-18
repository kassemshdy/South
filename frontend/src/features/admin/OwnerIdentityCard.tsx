import { UserRound } from 'lucide-react'

import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { GENDER_KEYS, MARITAL_STATUS_KEYS } from '@/features/identity/labels'
import { useI18n, type TranslationKey } from '@/i18n'
import type { OwnerIdentity } from '@/types/api'

/**
 * The owner's identity, as a reviewer sees it.
 *
 * Shared by the business and talent review pages: the identity belongs to the
 * account, so the same block appears wherever a reviewer checks a listing
 * against the ID document — and one component means the two can't drift into
 * labelling the same field differently.
 */
export function OwnerIdentityCard({ identity }: { identity: OwnerIdentity | null }) {
  const { t } = useI18n()

  const rows: { key: string; label: TranslationKey; value: string | null }[] = [
    { key: 'full_name', label: 'admin.fieldFullName', value: identity?.full_name ?? null },
    {
      key: 'birth_year',
      label: 'admin.fieldBirthYear',
      value:
        identity?.birth_year !== null && identity?.birth_year !== undefined
          ? String(identity.birth_year)
          : null,
    },
    {
      key: 'gender',
      label: 'admin.fieldGender',
      value: identity?.gender ? t(GENDER_KEYS[identity.gender]) : null,
    },
    {
      key: 'marital_status',
      label: 'admin.fieldMaritalStatus',
      value: identity?.marital_status ? t(MARITAL_STATUS_KEYS[identity.marital_status]) : null,
    },
    {
      key: 'registration_place',
      label: 'admin.fieldRegistrationPlace',
      value: identity?.registration_place ?? null,
    },
    {
      key: 'residence_place',
      label: 'admin.fieldResidencePlace',
      value: identity?.residence_place ?? null,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <h2 className="font-bold">{t('admin.identityHeading')}</h2>
      </CardHeader>
      <CardBody className="space-y-3">
        {identity === null ? (
          <p className="text-sm text-ink-500">{t('admin.identityNotProvided')}</p>
        ) : (
          <>
            {/* The face beside the name, which is the whole reason a reviewer
                sees either. It is not published anywhere — the API keeps it
                out of every public schema, pinned by test_identity.py. */}
            <div className="flex items-center gap-3 pb-1">
              <span className="h-20 w-20 shrink-0 overflow-hidden rounded-2xl border-2 border-dashed border-ink-100 bg-sand-50">
                {identity.photo_url ? (
                  <img src={identity.photo_url} alt="" className="h-full w-full object-cover" />
                ) : (
                  <span className="flex h-full items-center justify-center text-ink-300">
                    <UserRound className="h-6 w-6" aria-hidden="true" />
                  </span>
                )}
              </span>
              {!identity.photo_url ? (
                <p className="text-sm text-ink-300">{t('admin.identityNoPhoto')}</p>
              ) : null}
            </div>

            {rows.map((row) => (
            <div key={row.key}>
              <p className="text-sm font-semibold text-ink-700">{t(row.label)}</p>
              <p
                className={`mt-0.5 whitespace-pre-line ${
                  row.value ? 'text-ink-900' : 'text-ink-300'
                } ${row.key === 'birth_year' ? 'ltr-nums' : ''}`}
              >
                {row.value || t('common.notSet')}
              </p>
              </div>
            ))}
          </>
        )}
        <p className="text-xs text-ink-300">{t('admin.identityHint')}</p>
      </CardBody>
    </Card>
  )
}
