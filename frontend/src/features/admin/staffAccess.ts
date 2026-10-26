import { useAuth } from '@/features/auth/AuthContext'
import type { StaffRole } from '@/types/api'

/**
 * What a staff role may do, mirroring `backend/app/core/permissions.py`.
 *
 * Only for what the admin area *shows*: a button the person cannot use is
 * hidden rather than left to fail. The API enforces the same table whatever
 * this says, so a mismatch costs a 403, never access.
 */
export type StaffAction =
  | 'moderate' // approve, reject, suspend, correct a listing, delete a product
  | 'documents' // read ID scans, CVs and a business's papers
  | 'credentials' // issue an owner's password
  | 'support' // tickets, partner requests, set-aside applications
  | 'content' // pages, articles, covers, team, categories and places
  | 'manage' // staff, export, permanent deletes, site settings

const ALLOWED: Record<StaffAction, StaffRole[]> = {
  moderate: ['MANAGER', 'REVIEWER'],
  documents: ['MANAGER', 'REVIEWER'],
  credentials: ['MANAGER', 'REVIEWER', 'SUPPORT'],
  support: ['MANAGER', 'SUPPORT'],
  content: ['MANAGER', 'EDITOR'],
  manage: ['MANAGER'],
}

export const STAFF_ROLES: StaffRole[] = ['MANAGER', 'REVIEWER', 'SUPPORT', 'EDITOR', 'VIEWER']

export function staffCan(role: StaffRole | null | undefined, action: StaffAction): boolean {
  // An administrator with no role recorded is a viewer, as on the server.
  return ALLOWED[action].includes(role ?? 'VIEWER')
}

export function useStaffCan(action: StaffAction): boolean {
  const { user } = useAuth()
  return user?.role === 'ADMIN' && staffCan(user.staff_role, action)
}
