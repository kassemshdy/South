import { Check, Minus } from 'lucide-react'

import { Card, CardBody } from '@/components/ui/Card'
import { STAFF_ROLES, staffCan, type StaffAction } from '@/features/admin/staffAccess'
import { useT, type TranslationKey } from '@/i18n'
import type { StaffRole } from '@/types/api'

const ROLE_LABEL: Record<StaffRole, TranslationKey> = {
  MANAGER: 'staff.roleMANAGER',
  REVIEWER: 'staff.roleREVIEWER',
  SUPPORT: 'staff.roleSUPPORT',
  EDITOR: 'staff.roleEDITOR',
  VIEWER: 'staff.roleVIEWER',
}

/**
 * One row per thing a role may do. Every row but the first reads the same
 * table that hides buttons in the admin area (`staffAccess.ts`), so the
 * matrix cannot say something the screens do not; opening an owner's
 * account goes to the roles that moderate, as on the server.
 */
const ROWS: { label: TranslationKey; hint?: TranslationKey; action: StaffAction | 'read' }[] = [
  { label: 'staff.canRead', action: 'read' },
  { label: 'staff.canModerate', action: 'moderate' },
  { label: 'staff.canDocuments', action: 'documents' },
  { label: 'staff.canViewAs', hint: 'staff.canViewAsHint', action: 'moderate' },
  { label: 'staff.canCredentials', action: 'credentials' },
  { label: 'staff.canSupport', action: 'support' },
  { label: 'staff.canContent', action: 'content' },
  { label: 'staff.canManage', action: 'manage' },
]

/** What each staff role may do, as a table under the staff list. */
export function StaffPermissionsMatrix() {
  const t = useT()
  return (
    <Card>
      <CardBody className="space-y-3 p-5">
        <h2 className="font-bold">{t('staff.matrixTitle')}</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-ink-700">
                <th className="py-2 text-start font-semibold">{t('staff.matrixColumn')}</th>
                {STAFF_ROLES.map((role) => (
                  <th key={role} className="px-2 py-2 text-center font-semibold">
                    {t(ROLE_LABEL[role])}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label} className="border-b border-ink-50 last:border-0">
                  <td className="py-2.5 pe-3">
                    <span className="font-medium text-ink-900">{t(row.label)}</span>
                    {row.hint ? <span className="block text-xs text-ink-500">{t(row.hint)}</span> : null}
                  </td>
                  {STAFF_ROLES.map((role) => {
                    const allowed = row.action === 'read' || staffCan(role, row.action)
                    return (
                      <td key={role} className="px-2 py-2.5 text-center">
                        {allowed ? (
                          <Check
                            className="mx-auto h-5 w-5 rounded-full bg-olive-50 p-0.5 text-olive-700"
                            aria-label={t('staff.allowed')}
                          />
                        ) : (
                          <Minus className="mx-auto h-4 w-4 text-ink-200" aria-label={t('staff.denied')} />
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-500">{t('staff.matrixNote')}</p>
      </CardBody>
    </Card>
  )
}
