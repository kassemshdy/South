import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { ItemManager } from '@/features/items/ItemManager'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

export function ItemsPage() {
  const { id = '' } = useParams()
  const t = useT()
  useSeo({ title: t('itemsPage.seoTitle'), noIndex: true })

  const business = useQuery({
    queryKey: queryKeys.myBusiness(id),
    queryFn: () => ownerApi.get(id),
    enabled: id.length > 0,
  })

  if (business.isLoading) return <InlineSpinner />
  if (business.isError || !business.data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={business.error} onRetry={() => void business.refetch()} />
      </div>
    )
  }

  return (
    <div className="container-page max-w-3xl py-10">
      <Link to="/dashboard" className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700">
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t('wizard.backToDashboard')}
      </Link>

      <header className="mb-6">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-3xl">{t('itemsPage.heading')}</h1>
          <StatusBadge status={business.data.status} />
        </div>
        <p className="mt-2 text-ink-500">
          {business.data.name} ·{' '}
          <Link to={`/dashboard/businesses/${id}/edit`} className="text-brand-700 hover:underline">
            {t('itemsPage.editBusinessLink')}
          </Link>
        </p>
      </header>

      <Card>
        <CardBody>
          <ItemManager businessId={id} />
        </CardBody>
      </Card>
    </div>
  )
}
