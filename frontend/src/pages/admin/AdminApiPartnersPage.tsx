import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

/**
 * Keys to the read-only partner feed (`/api/partner/v1`, docs/PARTNER_API.md)
 * for Yalla Pay, AdsTalk and whoever follows. A key is shown once, when it is
 * issued or replaced -- the server keeps only its hash -- so it is held in
 * this component's state and nowhere else. Issuing is the manager's.
 */
export function AdminApiPartnersPage() {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const canManage = useStaffCan('manage')
  const [name, setName] = useState('')
  const [issued, setIssued] = useState<{ name: string; key: string } | null>(null)

  const partners = useQuery({ queryKey: queryKeys.adminApiPartners, queryFn: adminApi.apiPartners })
  const after = {
    onError: () => toast.error(t('states.errorFallback')),
  }
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.adminApiPartners })
  const issue = useMutation({
    mutationFn: () => adminApi.issueApiPartner(name.trim()),
    onSuccess: (data) => {
      setIssued({ name: data.name, key: data.api_key })
      setName('')
      refresh()
    },
    ...after,
  })
  const rotate = useMutation({
    mutationFn: adminApi.rotateApiPartner,
    onSuccess: (data) => {
      setIssued({ name: data.name, key: data.api_key })
      refresh()
    },
    ...after,
  })
  const revoke = useMutation({ mutationFn: adminApi.revokeApiPartner, onSuccess: refresh, ...after })

  const onIssue = (event: FormEvent) => {
    event.preventDefault()
    if (name.trim().length >= 2) issue.mutate()
  }

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.apiPartnersHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.apiPartnersSubtitle')}</p>
      </header>

      {issued ? (
        <Card>
          <CardBody className="space-y-2">
            <p className="font-semibold text-ink-900">{issued.name}</p>
            <p className="text-sm text-clay-700">{t('admin.apiPartnerKeyOnce')}</p>
            <code className="block select-all break-all rounded-lg bg-sand-100 p-3 text-sm" dir="ltr">
              {issued.key}
            </code>
          </CardBody>
        </Card>
      ) : null}

      {canManage ? (
        <form onSubmit={onIssue} className="flex flex-wrap items-end gap-2">
          <Field label={t('admin.apiPartnerName')} className="min-w-48 flex-1">
            {(field) => (
              <Input {...field} value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
            )}
          </Field>
          <Button type="submit" disabled={issue.isPending || name.trim().length < 2}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {t('admin.apiPartnerIssue')}
          </Button>
        </form>
      ) : null}

      {partners.isLoading ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : partners.isError ? (
        <ErrorState error={partners.error} onRetry={() => void partners.refetch()} />
      ) : partners.data && partners.data.length > 0 ? (
        <ul className="space-y-3">
          {partners.data.map((partner) => (
            <li key={partner.id}>
              <Card>
                <CardBody className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-ink-900">{partner.name}</p>
                    <p className="text-sm text-ink-500" dir="ltr">
                      {partner.key_prefix}… · {partner.scopes.join(' ')}
                    </p>
                    <p className="text-sm text-ink-500">
                      {!partner.active
                        ? t('admin.apiPartnerRevoked')
                        : partner.last_used_at
                          ? t('admin.apiPartnerLastUsed', { date: formatDate(partner.last_used_at, locale) })
                          : t('admin.apiPartnerNever')}
                    </p>
                  </div>
                  {canManage ? (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => rotate.mutate(partner.id)}>
                        {t('admin.apiPartnerRotate')}
                      </Button>
                      {partner.active ? (
                        <Button variant="ghost" size="sm" onClick={() => revoke.mutate(partner.id)}>
                          {t('admin.apiPartnerRevoke')}
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('admin.apiPartnersEmpty')} />
      )}
    </div>
  )
}
