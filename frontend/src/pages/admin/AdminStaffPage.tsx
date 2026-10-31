import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, MessageCircle, UserPlus } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { StaffPermissionsMatrix } from '@/features/admin/StaffPermissionsMatrix'
import { STAFF_ROLES } from '@/features/admin/staffAccess'
import { useAuth } from '@/features/auth/AuthContext'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { StaffPassword, StaffRole } from '@/types/api'
import { whatsappHref } from '@/utils/format'

const ROLE_LABEL: Record<StaffRole, TranslationKey> = {
  MANAGER: 'staff.roleMANAGER',
  REVIEWER: 'staff.roleREVIEWER',
  SUPPORT: 'staff.roleSUPPORT',
  EDITOR: 'staff.roleEDITOR',
  VIEWER: 'staff.roleVIEWER',
}

const ROLE_HINT: Record<StaffRole, TranslationKey> = {
  MANAGER: 'staff.hintMANAGER',
  REVIEWER: 'staff.hintREVIEWER',
  SUPPORT: 'staff.hintSUPPORT',
  EDITOR: 'staff.hintEDITOR',
  VIEWER: 'staff.hintVIEWER',
}

/**
 * The manager's page: who is on the staff, with what role, and inviting more.
 *
 * An invitation creates the account and shows its password once, with a
 * WhatsApp message ready to send -- the site sends no email or SMS, so this
 * is the same path an owner's password takes. The API refuses a manager
 * changing their own account and demoting the last manager.
 */
export function AdminStaffPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [form, setForm] = useState({ display_name: '', email: '', phone: '', staff_role: 'REVIEWER' as StaffRole })
  const [issued, setIssued] = useState<StaffPassword | null>(null)

  const staff = useQuery({ queryKey: queryKeys.adminStaff, queryFn: adminApi.staff })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.adminStaff })
  const failed = (error: unknown) =>
    toast.error(t('staff.failed'), error instanceof ApiError ? error.message : undefined)

  const invite = useMutation({
    mutationFn: () =>
      adminApi.inviteStaff({ ...form, phone: form.phone.trim() || undefined }),
    onSuccess: (result) => {
      setIssued(result)
      setForm({ display_name: '', email: '', phone: '', staff_role: 'REVIEWER' })
      refresh()
    },
    onError: failed,
  })
  const update = useMutation({
    mutationFn: ({ id, ...payload }: { id: string; staff_role?: StaffRole; is_active?: boolean }) =>
      adminApi.updateStaff(id, payload),
    onSuccess: () => {
      refresh()
      toast.success(t('staff.saved'))
    },
    onError: failed,
  })
  const reissue = useMutation({
    mutationFn: (id: string) => adminApi.reissueStaffPassword(id),
    onSuccess: setIssued,
    onError: failed,
  })

  return (
    <div className="max-w-4xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('staff.heading')}</h1>
        <p className="mt-2 text-ink-500">{t('staff.subtitle')}</p>
      </header>

      {issued ? <IssuedCard issued={issued} onDone={() => setIssued(null)} /> : null}

      <Card>
        <CardBody className="space-y-4 p-5">
          <h2 className="flex items-center gap-2 font-bold">
            <UserPlus className="h-5 w-5 text-brand-700" aria-hidden="true" />
            {t('staff.invite')}
          </h2>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              invite.mutate()
            }}
          >
            <Field label={t('staff.nameLabel')} required>
              {(props) => (
                <Input
                  {...props}
                  value={form.display_name}
                  onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                  required
                  minLength={2}
                />
              )}
            </Field>
            <Field label={t('staff.emailLabel')} required>
              {(props) => (
                <Input
                  {...props}
                  type="email"
                  dir="ltr"
                  value={form.email}
                  onChange={(event) => setForm({ ...form, email: event.target.value })}
                  required
                />
              )}
            </Field>
            <Field label={t('staff.phoneLabel')}>
              {(props) => (
                <Input
                  {...props}
                  type="tel"
                  dir="ltr"
                  className="ltr-nums"
                  placeholder="03 123 456"
                  value={form.phone}
                  onChange={(event) => setForm({ ...form, phone: event.target.value })}
                />
              )}
            </Field>
            <Field label={t('staff.roleLabel')} required hint={t(ROLE_HINT[form.staff_role])}>
              {(props) => (
                <Select
                  value={form.staff_role}
                  onValueChange={(value) => setForm({ ...form, staff_role: value as StaffRole })}
                >
                  <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STAFF_ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {t(ROLE_LABEL[role])}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" loading={invite.isPending}>
                {t('staff.invite')}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {staff.isLoading ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : staff.isError ? (
        <ErrorState error={staff.error} onRetry={() => void staff.refetch()} />
      ) : (
        <ul className="space-y-3">
          {(staff.data ?? []).map((member) => {
            const self = member.id === user?.id
            return (
              <li key={member.id}>
                <Card>
                  <CardBody className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div>
                      <p className="flex flex-wrap items-center gap-2 font-semibold">
                        {member.display_name ?? member.email}
                        {self ? <Badge className="bg-brand-100 text-brand-800">{t('staff.you')}</Badge> : null}
                        {member.is_active ? null : (
                          <Badge className="bg-ink-100 text-ink-600">{t('staff.disabled')}</Badge>
                        )}
                      </p>
                      <p className="text-sm text-ink-500" dir="ltr">
                        {member.email}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Select
                        value={member.staff_role ?? 'VIEWER'}
                        disabled={self || update.isPending}
                        onValueChange={(value) =>
                          update.mutate({ id: member.id, staff_role: value as StaffRole })
                        }
                      >
                        <SelectTrigger aria-label={t('staff.roleLabel')} className="w-40">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {STAFF_ROLES.map((role) => (
                            <SelectItem key={role} value={role}>
                              {t(ROLE_LABEL[role])}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {self ? null : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            loading={reissue.isPending && reissue.variables === member.id}
                            onClick={() => reissue.mutate(member.id)}
                          >
                            {t('credentials.reissue')}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              update.mutate({ id: member.id, is_active: !member.is_active })
                            }
                          >
                            {member.is_active ? t('staff.disable') : t('staff.enable')}
                          </Button>
                        </>
                      )}
                    </div>
                  </CardBody>
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      <StaffPermissionsMatrix />
    </div>
  )
}

function IssuedCard({ issued, onDone }: { issued: StaffPassword; onDone: () => void }) {
  const t = useT()
  const [copied, setCopied] = useState(false)
  const message = t('staff.whatsappMessage', {
    url: window.location.origin,
    email: issued.staff.email ?? '',
    password: issued.password,
  })
  const href = whatsappHref(issued.staff.personal_phone_number, message)

  return (
    <Card className="border-olive-200 bg-olive-50/40">
      <CardBody className="space-y-4 p-5">
        <p className="rounded-xl bg-clay-50 p-3.5 text-sm text-clay-800">{t('credentials.onceWarning')}</p>
        <dl className="space-y-2 rounded-xl border-2 border-dashed border-sand-300 bg-sand-50 p-4">
          <div>
            <dt className="text-xs text-ink-500">{t('staff.emailLabel')}</dt>
            <dd className="select-all font-semibold text-ink-900" dir="ltr">
              {issued.staff.email}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-500">{t('credentials.passwordLabel')}</dt>
            <dd className="select-all font-mono text-lg font-semibold tracking-wide text-ink-900" dir="ltr">
              {issued.password}
            </dd>
          </div>
        </dl>
        <div className="flex flex-wrap gap-3">
          {href ? (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-olive-600 px-4 py-2.5 font-semibold text-white hover:bg-olive-700"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              {t('credentials.sendOnWhatsapp')}
            </a>
          ) : null}
          <Button
            variant="outline"
            onClick={() => {
              void navigator.clipboard
                .writeText(message)
                .then(() => setCopied(true))
                .catch(() => undefined)
            }}
          >
            {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
            {copied ? t('credentials.copied') : t('credentials.copyMessage')}
          </Button>
          <Button variant="ghost" onClick={onDone}>
            {t('common.close')}
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}
