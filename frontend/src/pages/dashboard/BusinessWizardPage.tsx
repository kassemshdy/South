import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, PartyPopper, Send } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { BasicsForm } from '@/features/businesses/BasicsForm'
import { LocationForm } from '@/features/businesses/LocationForm'
import { SocialForm } from '@/features/businesses/SocialForm'
import { ImageManager } from '@/features/images/ImageManager'
import { ItemManager } from '@/features/items/ItemManager'
import { useSeo } from '@/hooks/useSeo'
import { ApiError } from '@/services/api/client'
import { ownerApi, type BusinessPayload } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { cn } from '@/utils/cn'

const STEPS = [
  { key: 'basics', label: 'المعلومات الأساسية' },
  { key: 'location', label: 'الموقع' },
  { key: 'images', label: 'الصور' },
  { key: 'social', label: 'التواصل الاجتماعي' },
  { key: 'items', label: 'المنتجات والخدمات' },
  { key: 'review', label: 'المراجعة والإرسال' },
] as const

type StepKey = (typeof STEPS)[number]['key']

/**
 * Multi-step creation flow.
 *
 * The listing is created as a DRAFT after step 1, so every later step is an
 * ordinary update and a half-finished wizard is never lost.
 */
export function BusinessWizardPage() {
  const [step, setStep] = useState<StepKey>('basics')
  const [businessId, setBusinessId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()

  useSeo({ title: 'أضف نشاطك التجاري | دليل الجنوب', noIndex: true })

  const business = useQuery({
    queryKey: queryKeys.myBusiness(businessId ?? ''),
    queryFn: () => ownerApi.get(businessId as string),
    enabled: businessId !== null,
  })

  const invalidate = () => {
    if (businessId) void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(businessId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const create = useMutation({
    mutationFn: (payload: BusinessPayload) => ownerApi.create(payload),
    onSuccess: (created) => {
      setBusinessId(created.id)
      queryClient.setQueryData(queryKeys.myBusiness(created.id), created)
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
      toast.success('تم حفظ نشاطك كمسودة')
      setStep('location')
    },
    onError: (error) =>
      toast.error('تعذر إنشاء النشاط', error instanceof ApiError ? error.message : undefined),
  })

  const update = useMutation({
    mutationFn: ({ payload, next }: { payload: Partial<BusinessPayload>; next: StepKey }) =>
      ownerApi.update(businessId as string, payload).then((result) => ({ result, next })),
    onSuccess: ({ result, next }) => {
      queryClient.setQueryData(queryKeys.myBusiness(result.id), result)
      invalidate()
      toast.success('تم الحفظ')
      setStep(next)
    },
    onError: (error) =>
      toast.error('تعذر الحفظ', error instanceof ApiError ? error.message : undefined),
  })

  const submit = useMutation({
    mutationFn: () => ownerApi.submit(businessId as string),
    onSuccess: () => {
      invalidate()
      toast.success('تم إرسال نشاطك للمراجعة.', 'سنقوم بمراجعته قبل ظهوره في الدليل.')
      navigate('/dashboard')
    },
    onError: (error) =>
      toast.error('لا يمكن الإرسال بعد', error instanceof ApiError ? error.message : undefined),
  })

  const currentIndex = STEPS.findIndex((item) => item.key === step)
  const data = business.data

  return (
    <div className="container-page max-w-3xl py-10">
      <header className="mb-8">
        <h1 className="text-3xl">أضف نشاطك التجاري</h1>
        <p className="mt-2 text-ink-500">
          املأ الخطوات التالية. يمكنك الحفظ والعودة لاحقاً في أي وقت.
        </p>
      </header>

      <ol className="mb-8 flex flex-wrap gap-2" aria-label="خطوات الإضافة">
        {STEPS.map((item, index) => {
          const isDone = index < currentIndex
          const isCurrent = item.key === step
          return (
            <li key={item.key}>
              <button
                type="button"
                // Steps after the first need a saved draft to act on.
                disabled={businessId === null && index > 0}
                onClick={() => setStep(item.key)}
                aria-current={isCurrent ? 'step' : undefined}
                className={cn(
                  'flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                  isCurrent
                    ? 'bg-clay-500 text-white'
                    : isDone
                      ? 'bg-olive-100 text-olive-700'
                      : 'bg-white text-ink-500 ring-1 ring-ink-100',
                )}
              >
                {isDone ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <span>{index + 1}</span>}
                {item.label}
              </button>
            </li>
          )
        })}
      </ol>

      <Card>
        <CardBody>
          {step === 'basics' ? (
            <BasicsForm
              business={data}
              submitLabel={businessId ? 'حفظ ومتابعة' : 'حفظ ومتابعة'}
              pending={create.isPending || update.isPending}
              onSubmit={(payload) =>
                businessId
                  ? update.mutate({ payload, next: 'location' })
                  : create.mutate(payload)
              }
            />
          ) : null}

          {businessId === null && step !== 'basics' ? (
            <p className="text-ink-500">احفظ المعلومات الأساسية أولاً.</p>
          ) : business.isLoading ? (
            <InlineSpinner />
          ) : (
            <>
              {step === 'location' && data ? (
                <LocationForm
                  business={data}
                  submitLabel="حفظ ومتابعة"
                  pending={update.isPending}
                  onSubmit={(payload) => update.mutate({ payload, next: 'images' })}
                  footer={
                    <Button type="button" variant="ghost" onClick={() => setStep('basics')}>
                      رجوع
                    </Button>
                  }
                />
              ) : null}

              {step === 'images' && data ? (
                <div className="space-y-6">
                  <ImageManager business={data} />
                  <div className="flex gap-3 border-t border-ink-100 pt-5">
                    <Button size="lg" onClick={() => setStep('social')}>
                      متابعة
                    </Button>
                    <Button variant="ghost" onClick={() => setStep('location')}>
                      رجوع
                    </Button>
                  </div>
                </div>
              ) : null}

              {step === 'social' && data ? (
                <SocialForm
                  business={data}
                  submitLabel="حفظ ومتابعة"
                  pending={update.isPending}
                  onSubmit={(payload) => update.mutate({ payload, next: 'items' })}
                  footer={
                    <Button type="button" variant="ghost" onClick={() => setStep('images')}>
                      رجوع
                    </Button>
                  }
                />
              ) : null}

              {step === 'items' && data ? (
                <div className="space-y-6">
                  <ItemManager businessId={data.id} />
                  <div className="flex gap-3 border-t border-ink-100 pt-5">
                    <Button size="lg" onClick={() => setStep('review')}>
                      متابعة للمراجعة
                    </Button>
                    <Button variant="ghost" onClick={() => setStep('social')}>
                      رجوع
                    </Button>
                  </div>
                </div>
              ) : null}

              {step === 'review' && data ? (
                <ReviewStep
                  businessId={data.id}
                  name={data.name}
                  onBack={() => setStep('items')}
                  onSubmit={() => submit.mutate()}
                  submitting={submit.isPending}
                />
              ) : null}
            </>
          )}
        </CardBody>
      </Card>

      {businessId ? (
        <p className="mt-4 text-center text-sm text-ink-500">
          نشاطك محفوظ كمسودة.{' '}
          <Link to="/dashboard" className="text-clay-600 hover:underline">
            العودة إلى نشاطاتي
          </Link>
        </p>
      ) : null}
    </div>
  )
}

function ReviewStep({
  businessId,
  name,
  onBack,
  onSubmit,
  submitting,
}: {
  businessId: string
  name: string
  onBack: () => void
  onSubmit: () => void
  submitting: boolean
}) {
  // The backend is the authority on completeness; we ask it rather than
  // duplicating the rule on the client.
  const readiness = useQuery({
    queryKey: queryKeys.readiness(businessId),
    queryFn: () => ownerApi.readiness(businessId),
  })

  const missing = readiness.data ?? []
  const ready = readiness.isSuccess && missing.length === 0

  return (
    <div className="space-y-6">
      <div className="text-center">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sand-100 text-clay-600">
          <PartyPopper className="h-7 w-7" aria-hidden="true" />
        </span>
        <h2 className="text-xl">جاهز لإرسال «{name}» للمراجعة؟</h2>
        <p className="mt-2 text-ink-500">
          سيراجع فريق الإدارة نشاطك قبل نشره في الدليل. يمكنك متابعة الحالة من صفحة نشاطاتي.
        </p>
      </div>

      {readiness.isLoading ? (
        <InlineSpinner label="جارٍ التحقق من اكتمال البيانات…" />
      ) : missing.length > 0 ? (
        <div className="rounded-xl border-2 border-sand-300 bg-sand-50 p-4">
          <p className="font-semibold text-clay-800">أكمل البيانات التالية قبل الإرسال:</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {missing.map((item) => (
              <li key={item}>
                <Badge className="bg-white text-clay-700">{item}</Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="rounded-xl border-2 border-olive-200 bg-olive-50 p-4 text-olive-800">
          جميع البيانات المطلوبة مكتملة.
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button size="lg" disabled={!ready} loading={submitting} onClick={onSubmit}>
          <Send className="h-5 w-5" aria-hidden="true" />
          إرسال للمراجعة
        </Button>
        <Button variant="ghost" onClick={onBack}>
          رجوع
        </Button>
      </div>
    </div>
  )
}
