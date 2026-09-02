import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ExternalLink, ListPlus, Pencil, Plus, Send, Store } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { ApiError } from '@/services/api/client'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { OwnerBusiness } from '@/types/api'
import { formatRelativeDate } from '@/utils/format'

export function DashboardPage() {
  const { user } = useAuth()
  useSeo({ title: 'نشاطاتي | دليل الجنوب', noIndex: true })

  const businesses = useQuery({ queryKey: queryKeys.myBusinesses, queryFn: ownerApi.list })

  return (
    <div className="container-page py-10">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">نشاطاتي</h1>
          <p className="mt-2 text-ink-500">
            مرحباً{user?.display_name ? ` ${user.display_name}` : ''}، أدِر نشاطاتك التجارية من هنا.
          </p>
        </div>
        <Button asChild size="lg">
          <Link to="/dashboard/businesses/new">
            <Plus className="h-5 w-5" aria-hidden="true" />
            إضافة نشاط جديد
          </Link>
        </Button>
      </header>

      {businesses.isLoading ? (
        <div className="grid gap-5 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <Skeleton key={index} className="h-56 rounded-2xl" />
          ))}
        </div>
      ) : businesses.isError ? (
        <ErrorState error={businesses.error} onRetry={() => void businesses.refetch()} />
      ) : businesses.data && businesses.data.length > 0 ? (
        <div className="grid gap-5 md:grid-cols-2">
          {businesses.data.map((business) => (
            <OwnerBusinessCard key={business.id} business={business} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Store className="h-7 w-7" aria-hidden="true" />}
          title="لم تُضف أي نشاط بعد"
          description="أنشئ صفحة نشاطك التجاري وأرسلها للمراجعة لتظهر في الدليل."
          action={
            <Button asChild size="lg">
              <Link to="/dashboard/businesses/new">أضف نشاطك التجاري</Link>
            </Button>
          }
        />
      )}
    </div>
  )
}

function OwnerBusinessCard({ business }: { business: OwnerBusiness }) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const submit = useMutation({
    mutationFn: () => ownerApi.submit(business.id),
    onSuccess: () => {
      toast.success(
        'تم إرسال نشاطك للمراجعة.',
        'سنقوم بمراجعته قبل ظهوره في الدليل.',
      )
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
    },
    onError: (error) => {
      // A 422 lists the fields the owner still needs to fill in.
      const message = error instanceof ApiError ? error.message : 'تعذر إرسال النشاط.'
      toast.error('لا يمكن الإرسال بعد', message)
    },
  })

  const canSubmit = business.status === 'DRAFT' || business.status === 'REJECTED'

  return (
    <Card className="flex flex-col">
      <CardBody className="flex flex-1 flex-col">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-sand-100">
            {business.logo_url ? (
              <img src={business.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <Store className="h-7 w-7" aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold">{business.name}</h2>
              <StatusBadge status={business.status} />
            </div>
            <p className="mt-1 text-sm text-ink-500">
              {business.category?.name_ar ?? 'بدون تصنيف'}
              {business.location ? ` · ${business.location.name_ar}` : ''}
            </p>
            <p className="mt-0.5 text-xs text-ink-300">
              آخر تحديث: {formatRelativeDate(business.updated_at)}
            </p>
          </div>
        </div>

        {business.status === 'REJECTED' && business.rejection_reason ? (
          <div className="mt-4 flex gap-2.5 rounded-xl border-2 border-clay-200 bg-clay-50 p-3.5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-clay-900">يحتاج إلى تعديل</p>
              <p className="mt-0.5 text-sm leading-relaxed text-clay-700">{business.rejection_reason}</p>
            </div>
          </div>
        ) : null}

        {business.status === 'PENDING_REVIEW' ? (
          <p className="mt-4 rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
            نشاطك قيد المراجعة من فريق الإدارة. سيظهر في الدليل فور الموافقة عليه.
          </p>
        ) : null}

        {business.status === 'SUSPENDED' ? (
          <p className="mt-4 rounded-xl bg-ink-100 p-3.5 text-sm text-ink-700">
            تم إيقاف نشاطك مؤقتاً. تواصل مع الإدارة لمزيد من التفاصيل.
          </p>
        ) : null}

        <div className="mt-5 flex flex-wrap gap-2 pt-1">
          <Button asChild variant="outline" size="sm">
            <Link to={`/dashboard/businesses/${business.id}/edit`}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              تعديل النشاط
            </Link>
          </Button>

          <Button asChild variant="outline" size="sm">
            <Link to={`/dashboard/businesses/${business.id}/items`}>
              <ListPlus className="h-4 w-4" aria-hidden="true" />
              إدارة المنتجات ({business.items.length})
            </Link>
          </Button>

          {business.status === 'APPROVED' ? (
            <Button asChild variant="ghost" size="sm">
              <Link to={`/business/${encodeURIComponent(business.slug)}`}>
                <ExternalLink className="h-4 w-4" aria-hidden="true" />
                الصفحة العامة
              </Link>
            </Button>
          ) : null}

          {canSubmit ? (
            <Button size="sm" loading={submit.isPending} onClick={() => submit.mutate()}>
              <Send className="h-4 w-4" aria-hidden="true" />
              إرسال للمراجعة
            </Button>
          ) : null}
        </div>

        {canSubmit && submit.error instanceof ApiError && submit.error.missing.length > 0 ? (
          <div className="mt-3 rounded-xl border border-sand-300 bg-sand-50 p-3">
            <p className="text-sm font-semibold text-clay-800">أكمل البيانات التالية أولاً:</p>
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {submit.error.missing.map((item) => (
                <li key={item}>
                  <Badge className="bg-white text-clay-700">{item}</Badge>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardBody>
    </Card>
  )
}
