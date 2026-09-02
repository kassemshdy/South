import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, ExternalLink, PauseCircle, PlayCircle, X } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router-dom'
import type { z } from 'zod'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Dialog, DialogClose, DialogContent } from '@/components/ui/Dialog'
import { Field } from '@/components/ui/Field'
import { Textarea } from '@/components/ui/Input'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, formatPrice, PLATFORM_LABELS, STATUS_LABELS } from '@/utils/format'
import { rejectSchema } from '@/utils/validation'

type RejectValues = z.infer<typeof rejectSchema>
type ConfirmAction = 'approve' | 'reject' | 'suspend' | 'reactivate' | null

export function AdminReviewPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [confirming, setConfirming] = useState<ConfirmAction>(null)

  const business = useQuery({
    queryKey: queryKeys.adminBusiness(id),
    queryFn: () => adminApi.get(id),
    enabled: id.length > 0,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminBusiness(id) })
    void queryClient.invalidateQueries({ queryKey: ['admin'] })
  }

  const act = useMutation({
    mutationFn: ({ action, reason }: { action: Exclude<ConfirmAction, null>; reason?: string }) => {
      switch (action) {
        case 'approve':
          return adminApi.approve(id)
        case 'reject':
          return adminApi.reject(id, reason ?? '')
        case 'suspend':
          return adminApi.suspend(id, reason)
        case 'reactivate':
          return adminApi.reactivate(id)
      }
    },
    onSuccess: (result) => {
      invalidate()
      setConfirming(null)
      toast.success(`تم تحديث حالة النشاط إلى «${STATUS_LABELS[result.status]}»`)
    },
    onError: (error) =>
      toast.error('تعذر تنفيذ الإجراء', error instanceof ApiError ? error.message : undefined),
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RejectValues>({ resolver: zodResolver(rejectSchema) })

  if (business.isLoading) return <InlineSpinner />
  if (business.isError || !business.data) {
    return <ErrorState error={business.error} onRetry={() => void business.refetch()} />
  }

  const data = business.data

  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/admin/businesses" className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-clay-600">
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        العودة إلى النشاطات
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-sand-100">
            {data.logo_url ? <img src={data.logo_url} alt="" className="h-full w-full object-cover" /> : null}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl">{data.name}</h1>
              <StatusBadge status={data.status} />
            </div>
            <p className="mt-1 text-sm text-ink-500">
              أُرسل للمراجعة: {formatDate(data.submitted_at)}
            </p>
          </div>
        </div>

        {data.status === 'APPROVED' ? (
          <Button asChild variant="outline" size="sm">
            <Link to={`/business/${encodeURIComponent(data.slug)}`}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              الصفحة العامة
            </Link>
          </Button>
        ) : null}
      </header>

      {/* Decision bar, pinned near the top: the admin's job on this page. */}
      <Card className="border-clay-200 bg-clay-50/40">
        <CardBody className="flex flex-wrap gap-3">
          {data.status === 'PENDING_REVIEW' ? (
            <>
              <Button size="lg" onClick={() => setConfirming('approve')}>
                <Check className="h-5 w-5" aria-hidden="true" />
                موافقة
              </Button>
              <Button
                size="lg"
                variant="danger"
                onClick={() => {
                  reset()
                  setConfirming('reject')
                }}
              >
                <X className="h-5 w-5" aria-hidden="true" />
                رفض
              </Button>
            </>
          ) : null}

          {data.status === 'APPROVED' ? (
            <Button size="lg" variant="outline" onClick={() => setConfirming('suspend')}>
              <PauseCircle className="h-5 w-5" aria-hidden="true" />
              إيقاف النشاط
            </Button>
          ) : null}

          {data.status === 'SUSPENDED' ? (
            <Button size="lg" onClick={() => setConfirming('reactivate')}>
              <PlayCircle className="h-5 w-5" aria-hidden="true" />
              إعادة التفعيل
            </Button>
          ) : null}

          {data.status === 'DRAFT' || data.status === 'REJECTED' ? (
            <p className="text-ink-500">
              {data.status === 'DRAFT'
                ? 'هذا النشاط ما زال مسودة لدى صاحبه ولم يُرسل للمراجعة.'
                : 'تم رفض هذا النشاط. بانتظار تعديل صاحبه وإعادة إرساله.'}
            </p>
          ) : null}
        </CardBody>
      </Card>

      {data.rejection_reason ? (
        <Card className="border-clay-200">
          <CardBody>
            <p className="font-semibold text-clay-900">سبب الرفض المُسجّل</p>
            <p className="mt-1 text-clay-700">{data.rejection_reason}</p>
          </CardBody>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="font-bold">معلومات النشاط</h2>
            </CardHeader>
            <CardBody className="space-y-3">
              <Detail label="الوصف المختصر" value={data.short_description} />
              <Detail label="النبذة" value={data.description} />
              <Detail label="التصنيف" value={data.category?.name_ar ?? null} />
              <Detail label="الموقع" value={data.location?.name_ar ?? null} />
              <Detail label="العنوان" value={data.address_text} />
              <Detail label="هاتف النشاط" value={data.phone} ltr />
              <Detail label="واتساب النشاط" value={data.whatsapp} ltr />
              <Detail label="البريد الإلكتروني" value={data.email} ltr />
              <Detail label="الموقع الإلكتروني" value={data.website} ltr />
            </CardBody>
          </Card>

          {data.images.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">معرض الصور ({data.images.length})</h2>
              </CardHeader>
              <CardBody>
                <div className="grid grid-cols-3 gap-2">
                  {data.images.map((image) => (
                    <a key={image.id} href={image.url} target="_blank" rel="noopener noreferrer">
                      <img src={image.url} alt="" className="h-24 w-full rounded-lg object-cover" />
                    </a>
                  ))}
                </div>
              </CardBody>
            </Card>
          ) : null}

          {data.items.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">المنتجات والخدمات ({data.items.length})</h2>
              </CardHeader>
              <CardBody>
                <ul className="divide-y divide-ink-100">
                  {data.items.map((item) => (
                    <li key={item.id} className="flex items-start justify-between gap-3 py-3">
                      <div>
                        <p className="font-semibold">{item.title}</p>
                        {item.description ? <p className="text-sm text-ink-500">{item.description}</p> : null}
                        {!item.is_available ? <p className="text-xs text-ink-500">غير متوفر</p> : null}
                      </div>
                      <span className="ltr-nums shrink-0 font-bold text-clay-700">
                        {formatPrice(item.price, item.currency) ?? '—'}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          ) : null}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="font-bold">صاحب النشاط</h2>
            </CardHeader>
            <CardBody className="space-y-3">
              <Detail label="الاسم" value={data.owner_display_name} />
              <Detail label="رقم الحساب" value={data.owner_phone} ltr />
              <p className="text-xs text-ink-300">
                رقم الحساب لا يظهر للزوار — تُنشر فقط أرقام التواصل المدخلة في النشاط.
              </p>
            </CardBody>
          </Card>

          {data.social_links.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">روابط التواصل</h2>
              </CardHeader>
              <CardBody className="space-y-2">
                {data.social_links.map((link) => (
                  <a
                    key={link.platform}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block truncate text-sm text-clay-600 hover:underline"
                  >
                    {PLATFORM_LABELS[link.platform]}: <span className="ltr-nums">{link.url}</span>
                  </a>
                ))}
              </CardBody>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <h2 className="font-bold">سجل المراجعة</h2>
            </CardHeader>
            <CardBody>
              {data.moderation_actions.length === 0 ? (
                <p className="text-sm text-ink-500">لا توجد إجراءات بعد.</p>
              ) : (
                <ol className="space-y-3">
                  {data.moderation_actions.map((action) => (
                    <li key={action.id} className="border-s-2 border-ink-100 ps-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className="bg-sand-100 text-clay-700">
                          {STATUS_LABELS[action.to_status]}
                        </Badge>
                        <span className="text-xs text-ink-300">{formatDate(action.created_at)}</span>
                      </div>
                      {action.reason ? <p className="mt-1 text-sm text-ink-500">{action.reason}</p> : null}
                    </li>
                  ))}
                </ol>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      <Dialog open={confirming !== null} onOpenChange={(open) => !open && setConfirming(null)}>
        {confirming === 'reject' ? (
          <DialogContent title="رفض النشاط" description={`سيظهر السبب لصاحب «${data.name}» ليتمكن من التعديل.`}>
            <form
              onSubmit={handleSubmit(({ reason }) => act.mutate({ action: 'reject', reason }))}
              className="space-y-4"
              noValidate
            >
              <Field label="سبب الرفض" required error={errors.reason?.message}>
                {(props) => (
                  <Textarea
                    {...props}
                    {...register('reason')}
                    rows={4}
                    placeholder="مثال: الرجاء إضافة صورة شعار أوضح ووصف أدق للخدمات."
                    invalid={Boolean(errors.reason)}
                    autoFocus
                  />
                )}
              </Field>
              <div className="flex gap-3">
                <Button type="submit" variant="danger" block loading={act.isPending}>
                  تأكيد الرفض
                </Button>
                <DialogClose asChild>
                  <Button type="button" variant="outline" block>
                    إلغاء
                  </Button>
                </DialogClose>
              </div>
            </form>
          </DialogContent>
        ) : confirming !== null ? (
          <DialogContent
            title={
              confirming === 'approve'
                ? 'تأكيد الموافقة'
                : confirming === 'suspend'
                  ? 'تأكيد إيقاف النشاط'
                  : 'تأكيد إعادة التفعيل'
            }
            description={
              confirming === 'approve'
                ? `سيصبح «${data.name}» ظاهراً للجميع في الدليل فوراً.`
                : confirming === 'suspend'
                  ? `سيُخفى «${data.name}» من الدليل ومن نتائج البحث.`
                  : `سيعود «${data.name}» للظهور في الدليل.`
            }
          >
            <div className="flex gap-3">
              <Button
                block
                variant={confirming === 'suspend' ? 'danger' : 'primary'}
                loading={act.isPending}
                onClick={() => act.mutate({ action: confirming })}
              >
                تأكيد
              </Button>
              <DialogClose asChild>
                <Button variant="outline" block>
                  إلغاء
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  )
}

function Detail({ label, value, ltr }: { label: string; value: string | null; ltr?: boolean }) {
  return (
    <div>
      <p className="text-sm font-semibold text-ink-700">{label}</p>
      <p className={`mt-0.5 whitespace-pre-line ${value ? 'text-ink-900' : 'text-ink-300'} ${ltr ? 'ltr-nums' : ''}`}>
        {value || 'غير محدد'}
      </p>
    </div>
  )
}
