import { useQuery } from '@tanstack/react-query'

import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { DeleteForeverButton } from '@/features/admin/DeleteForeverButton'
import { useI18n } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate } from '@/utils/format'

/**
 * What the partner form brought in (round 3), newest first. Administrators
 * only: each one is a stranger's name and phone number.
 */
export function AdminPartnersPage() {
  const { t, locale } = useI18n()
  const partners = useQuery({ queryKey: queryKeys.adminPartners, queryFn: adminApi.partners })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.partnersHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.partnersSubtitle')}</p>
      </header>

      {partners.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : partners.isError ? (
        <ErrorState error={partners.error} onRetry={() => void partners.refetch()} />
      ) : partners.data && partners.data.length > 0 ? (
        <ul className="space-y-3">
          {partners.data.map((entry) => (
            <li key={entry.id}>
              <Card>
                <CardBody className="space-y-2">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink-900">{entry.name}</p>
                      <p className="ltr-nums text-sm text-ink-500" dir="ltr">
                        {entry.phone}
                      </p>
                    </div>
                    <span className="text-xs text-ink-300">
                      {formatDate(entry.created_at, locale)}
                    </span>
                  </div>
                  <p className="text-sm text-ink-700">
                    <span className="font-semibold">{t('partner.occupationLabel')}: </span>
                    {entry.occupation}
                  </p>
                  <p className="text-sm text-ink-700">
                    <span className="font-semibold">{t('partner.residenceLabel')}: </span>
                    {entry.residence}
                  </p>
                  <div>
                    <p className="text-sm font-semibold text-ink-700">{t('partner.offerLabel')}</p>
                    <p className="whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
                      {entry.offer}
                    </p>
                  </div>
                  <div className="flex justify-end">
                    <DeleteForeverButton
                      size="sm"
                      description={t('admin.partnerDeleteBody')}
                      onDelete={() => adminApi.deletePartner(entry.id)}
                    />
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('admin.partnersEmpty')} />
      )}
    </div>
  )
}
