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
          rows.map((row) => (
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
          ))
        )}
        <p className="text-xs text-ink-300">{t('admin.identityHint')}</p>
      </CardBody>
    </Card>
  )
}
