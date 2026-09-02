import * as Tabs from '@radix-ui/react-tabs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowRight, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Dialog, DialogClose, DialogContent, DialogTrigger } from '@/components/ui/Dialog'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { BasicsForm } from '@/features/businesses/BasicsForm'
import { LocationForm } from '@/features/businesses/LocationForm'
import { SocialForm } from '@/features/businesses/SocialForm'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { ImageManager } from '@/features/images/ImageManager'
import { useSeo } from '@/hooks/useSeo'
import { ApiError } from '@/services/api/client'
import { ownerApi, type BusinessPayload } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { cn } from '@/utils/cn'

const TABS = [
  { value: 'basics', label: 'المعلومات الأساسية' },
  { value: 'location', label: 'الموقع' },
  { value: 'images', label: 'الصور' },
  { value: 'social', label: 'التواصل الاجتماعي' },
]

export function EditBusinessPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()
  const [tab, setTab] = useState('basics')

  useSeo({ title: 'تعديل النشاط | دليل الجنوب', noIndex: true })

  const business = useQuery({
    queryKey: queryKeys.myBusiness(id),
    queryFn: () => ownerApi.get(id),
    enabled: id.length > 0,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(id) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const update = useMutation({
    mutationFn: (payload: Partial<BusinessPayload>) => ownerApi.update(id, payload),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.myBusiness(id), result)
      invalidate()
      toast.success('تم حفظ التعديلات')
    },
    onError: (error) =>
      toast.error('تعذر الحفظ', error instanceof ApiError ? error.message : undefined),
  })

  const submit = useMutation({
    mutationFn: () => ownerApi.submit(id),
    onSuccess: () => {
      invalidate()
      toast.success('تم إرسال نشاطك للمراجعة.', 'سنقوم بمراجعته قبل ظهوره في الدليل.')
      navigate('/dashboard')
    },
    onError: (error) =>
      toast.error('لا يمكن الإرسال بعد', error instanceof ApiError ? error.message : undefined),
  })

  const remove = useMutation({
    mutationFn: () => ownerApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
      toast.success('تم حذف النشاط')
      navigate('/dashboard')
    },
    onError: (error) =>
      toast.error('تعذر الحذف', error instanceof ApiError ? error.message : undefined),
  })

  if (business.isLoading) return <InlineSpinner />
  if (business.isError || !business.data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={business.error} onRetry={() => void business.refetch()} />
      </div>
    )
  }

  const data = business.data
  const canSubmit = data.status === 'DRAFT' || data.status === 'REJECTED'

  return (
    <div className="container-page max-w-3xl py-10">
      <Link to="/dashboard" className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-clay-600">
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        العودة إلى نشاطاتي
      </Link>

      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl">{data.name}</h1>
            <StatusBadge status={data.status} />
          </div>
          <p className="mt-1.5 text-ink-500">
            <Link to={`/dashboard/businesses/${id}/items`} className="text-clay-600 hover:underline">
              إدارة المنتجات والخدمات ({data.items.length})
            </Link>
          </p>
        </div>

        {canSubmit ? (
          <Button loading={submit.isPending} onClick={() => submit.mutate()}>
            <Send className="h-4 w-4" aria-hidden="true" />
            إرسال للمراجعة
          </Button>
        ) : null}
      </header>

      {data.status === 'REJECTED' && data.rejection_reason ? (
        <div className="mb-6 flex gap-2.5 rounded-xl border-2 border-clay-200 bg-clay-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
          <div>
            <p className="font-semibold text-clay-900">يحتاج إلى تعديل</p>
            <p className="mt-0.5 leading-relaxed text-clay-700">{data.rejection_reason}</p>
            <p className="mt-2 text-sm text-clay-700">
              عدّل البيانات المطلوبة ثم اضغط «إرسال للمراجعة» مرة أخرى.
            </p>
          </div>
        </div>
      ) : null}

      <Card>
        <Tabs.Root value={tab} onValueChange={setTab}>
          <Tabs.List className="flex gap-1 overflow-x-auto border-b border-ink-100 p-2" aria-label="أقسام التعديل">
            {TABS.map((item) => (
              <Tabs.Trigger
                key={item.value}
                value={item.value}
                className={cn(
                  'whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-semibold text-ink-500 transition-colors',
                  'data-[state=active]:bg-sand-100 data-[state=active]:text-clay-700',
                )}
              >
                {item.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <CardBody>
            <Tabs.Content value="basics">
              <BasicsForm business={data} submitLabel="حفظ التعديلات" pending={update.isPending} onSubmit={(payload) => update.mutate(payload)} />
            </Tabs.Content>
            <Tabs.Content value="location">
              <LocationForm business={data} submitLabel="حفظ التعديلات" pending={update.isPending} onSubmit={(payload) => update.mutate(payload)} />
            </Tabs.Content>
            <Tabs.Content value="images">
              <ImageManager business={data} />
            </Tabs.Content>
            <Tabs.Content value="social">
              <SocialForm business={data} submitLabel="حفظ التعديلات" pending={update.isPending} onSubmit={(payload) => update.mutate(payload)} />
            </Tabs.Content>
          </CardBody>
        </Tabs.Root>
      </Card>

      <div className="mt-8 rounded-2xl border-2 border-clay-100 bg-clay-50/50 p-5">
        <h2 className="font-bold text-clay-900">حذف النشاط</h2>
        <p className="mt-1 text-sm text-clay-700">
          سيؤدي الحذف إلى إزالة النشاط وصوره ومنتجاته نهائياً. لا يمكن التراجع عن هذا الإجراء.
        </p>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="danger" size="sm" className="mt-4">
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              حذف النشاط
            </Button>
          </DialogTrigger>
          <DialogContent
            title="تأكيد حذف النشاط"
            description={`سيتم حذف «${data.name}» وكل صوره ومنتجاته نهائياً.`}
          >
            <div className="flex gap-3">
              <Button variant="danger" block loading={remove.isPending} onClick={() => remove.mutate()}>
                نعم، احذف النشاط
              </Button>
              <DialogClose asChild>
                <Button variant="outline" block>
                  إلغاء
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}
