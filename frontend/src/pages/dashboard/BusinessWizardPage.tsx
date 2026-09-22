import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, PartyPopper, Send, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { BasicsForm } from '@/features/businesses/BasicsForm'
import { DocumentManager } from '@/features/businesses/DocumentManager'
import { LocationForm } from '@/features/businesses/LocationForm'
import { SocialForm } from '@/features/businesses/SocialForm'
import { ImageManager } from '@/features/images/ImageManager'
import { useAuth } from '@/features/auth/AuthContext'
import { AssistedListing } from '@/features/onboarding/AssistedListing'
import { ItemManager } from '@/features/items/ItemManager'
import { OfferSwitcher } from '@/features/onboarding/OfferSwitcher'
import { originFromParams } from '@/features/onboarding/destinations'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { ownerApi, type BusinessPayload } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { cn } from '@/utils/cn'

// `optional` marks the steps nothing in `SUBMISSION_REQUIREMENTS` depends on.
// Unlabelled chips read as obligations; two of these are not, and an owner who
// does not sell individual products or keep a social page should be able to
// see that at a glance rather than walking through to find out.
//
// **Personal info comes first**, which is the order asked for: who you are,
// then what the business is, then what it sells. It is first for a reason
// beyond sequence — it is the one step that is not about this listing at all.
// The identity and the photo live on the account and are shared by every
// business it owns, so the step is a check rather than a form: fill it once
// and every later listing skips past it already satisfied.
//
// Social stays *after* images rather than joining location in a "profile"
// group, which was tried and reverted. Grouping them reads well but puts an
// optional step in front of a required one: the logo is the last thing the
// API needs before review, and the shortest path to submittable should not
// detour through a step nobody has to fill. `e2e/lean-onboarding.spec.ts`
// exists to protect exactly that path, and it is what caught the mistake.
const STEPS = [
  { key: 'personal', labelKey: 'wizard.stepPersonal' },
  { key: 'basics', labelKey: 'wizard.stepBasics' },
  { key: 'location', labelKey: 'wizard.stepLocation' },
  { key: 'images', labelKey: 'wizard.stepImages' },
  { key: 'social', labelKey: 'wizard.stepSocial', optional: true },
  { key: 'documents', labelKey: 'wizard.stepDocuments', optional: true },
  { key: 'items', labelKey: 'wizard.stepItems', optional: true },
  { key: 'review', labelKey: 'wizard.stepReview' },
] as const satisfies readonly {
  key: string
  labelKey: TranslationKey
  optional?: boolean
}[]

type StepKey = (typeof STEPS)[number]['key']

/**
 * Multi-step creation flow.
 *
 * The listing is created as a DRAFT after step 1, so every later step is an
 * ordinary update and a half-finished wizard is never lost.
 */
/**
 * Step one: who is listing this.
 *
 * Deliberately a summary with a link rather than a copy of the account form.
 * The legal name, the civil-record places and the photo live on the account
 * and are shared by every business it owns — duplicating the inputs here
 * would give two places to edit one fact, and the second listing an owner
 * creates would ask for it all again. So this reads the account, says what is
 * still missing, and sends them to the one page that owns those fields.
 *
 * Nothing here blocks the wizard. The submission requirements the API
 * enforces are about the *listing*; identity is checked by a person at review
 * time, and an owner who wants to fill in their business first and come back
 * should be able to.
 */
function PersonalStep({ onContinue }: { onContinue: () => void }) {
  const { user } = useAuth()
  const t = useT()

  const missing = [
    !user?.full_name && t('wizard.personalMissingName'),
    !user?.photo_url && t('wizard.personalMissingPhoto'),
  ].filter((entry): entry is string => Boolean(entry))

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-ink-900">{t('wizard.personalHeading')}</h2>
        <p className="mt-2 text-ink-500">{t('wizard.personalIntro')}</p>
      </div>

      <div className="flex items-center gap-4 rounded-2xl bg-sand-50 p-4">
        <span className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl border-2 border-dashed border-ink-100 bg-white">
          {user?.photo_url ? (
            <img src={user.photo_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <span className="flex h-full items-center justify-center text-ink-300">
              <UserRound className="h-6 w-6" aria-hidden="true" />
            </span>
          )}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink-900">
            {user?.full_name ?? t('wizard.personalNoName')}
          </p>
          {missing.length > 0 ? (
            <p className="mt-0.5 text-sm text-clay-700">
              {t('wizard.personalMissing', { fields: missing.join(t('common.listSeparator')) })}
            </p>
          ) : (
            <p className="mt-0.5 text-sm text-olive-700">{t('wizard.personalComplete')}</p>
          )}
        </div>
      </div>

      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        {t('wizard.personalPrivacyNote')}
      </p>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button size="lg" onClick={onContinue}>
          {t('common.continue')}
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link to="/dashboard/account">
            <UserRound className="h-4 w-4" aria-hidden="true" />
            {t('wizard.personalEdit')}
          </Link>
        </Button>
      </div>
    </div>
  )
}

export function BusinessWizardPage() {
  const [step, setStep] = useState<StepKey>('personal')
  const [businessId, setBusinessId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()
  const t = useT()
  const [searchParams] = useSearchParams()
  const origin = originFromParams(searchParams)

  useSeo({ title: t('wizard.seoTitle'), noIndex: true })

  const business = useQuery({
    queryKey: queryKeys.myBusiness(businessId ?? ''),
    queryFn: () => ownerApi.get(businessId as string),
    enabled: businessId !== null,
  })

  const invalidate = () => {
    if (businessId) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(businessId) })
      // Readiness changes with almost every save — a logo upload alone can
      // complete the listing — so the shortcut below has to be re-checked.
      void queryClient.invalidateQueries({ queryKey: queryKeys.readiness(businessId) })
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const create = useMutation({
    mutationFn: (payload: BusinessPayload) => ownerApi.create(payload),
    onSuccess: (created) => {
      setBusinessId(created.id)
      queryClient.setQueryData(queryKeys.myBusiness(created.id), created)
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
      toast.success(t('wizard.draftSaved'))
      setStep('location')
    },
    onError: (error) =>
      toast.error(t('wizard.createFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const update = useMutation({
    mutationFn: ({ payload, next }: { payload: Partial<BusinessPayload>; next: StepKey }) =>
      ownerApi.update(businessId as string, payload).then((result) => ({ result, next })),
    onSuccess: ({ result, next }) => {
      queryClient.setQueryData(queryKeys.myBusiness(result.id), result)
      invalidate()
      toast.success(t('wizard.saved'))
      setStep(next)
    },
    onError: (error) =>
      toast.error(t('wizard.saveFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = useMutation({
    mutationFn: () => ownerApi.submit(businessId as string),
    onSuccess: () => {
      invalidate()
      toast.success(t('dashboard.submitted'), t('dashboard.submittedDescription'))
      navigate('/dashboard')
    },
    onError: (error) =>
      toast.error(
        t('dashboard.submitBlocked'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const currentIndex = STEPS.findIndex((item) => item.key === step)
  const data = business.data

  // The backend owns the definition of "complete", so the shortcut asks it
  // rather than re-deriving the rule here.
  const readiness = useQuery({
    queryKey: queryKeys.readiness(businessId ?? ''),
    queryFn: () => ownerApi.readiness(businessId as string),
    enabled: businessId !== null,
  })
  const readyToSubmit = readiness.isSuccess && readiness.data.length === 0

  return (
    <div className="container-page max-w-3xl py-10">
      <header className="mb-8">
        <h1 className="text-3xl">{t('wizard.heading')}</h1>
        <p className="mt-2 text-ink-500">{t('wizard.subtitle')}</p>
      </header>

      {/* Only until the listing exists. Step one writes a DRAFT, and offering
          to walk across to the talent form after that would leave a stub
          listing behind rather than simply changing your mind. Before the
          first save there is nothing to lose, and this is where a
          craftsperson who tapped the wrong card finds out. */}
      {businessId === null ? (
        <OfferSwitcher current={origin === 'IMPORTED' ? 'imported' : 'business'} />
      ) : null}

      <ol className="mb-8 flex flex-wrap gap-2" aria-label={t('wizard.stepsAria')}>
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
                    ? 'bg-brand-800 text-white'
                    : isDone
                      ? 'bg-olive-100 text-olive-700'
                      : 'bg-white text-ink-500 ring-1 ring-ink-100',
                )}
              >
                {isDone ? (
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <span>{index + 1}</span>
                )}
                {t(item.labelKey)}
                {'optional' in item && item.optional ? (
                  <span
                    className={cn(
                      'text-xs font-normal',
                      isCurrent ? 'text-white/80' : 'text-ink-300',
                    )}
                  >
                    {t('wizard.optionalStep')}
                  </span>
                ) : null}
              </button>
            </li>
          )
        })}
      </ol>

      {/* The whole point of #34: once the required six are in, stop walking
          the owner through steps that cannot block them. The banner appears
          the moment the listing is submittable and stays out of the way
          otherwise. */}
      {readyToSubmit && step !== 'review' ? (
        <div className="mb-6 rounded-2xl border-2 border-olive-200 bg-olive-50 p-5">
          <p className="font-bold text-olive-900">{t('wizard.readyTitle')}</p>
          <p className="mt-1 text-sm leading-relaxed text-olive-800">
            {t('wizard.readyBody')}
          </p>
          <Button
            type="button"
            variant="secondary"
            className="mt-4"
            onClick={() => setStep('review')}
          >
            <Send className="h-4 w-4" aria-hidden="true" />
            {t('wizard.readyCta')}
          </Button>
        </div>
      ) : null}

      <Card>
        <CardBody>
          {step === 'personal' ? <PersonalStep onContinue={() => setStep('basics')} /> : null}

          {step === 'basics' ? (
            <BasicsForm
              // Remounted when the switcher changes door before the first
              // save, so the form starts from the door now chosen.
              key={businessId ?? origin ?? 'LOCAL'}
              defaultOrigin={origin}
              serverError={create.error ?? update.error}
              business={data}
              submitLabel={t('wizard.saveAndContinue')}
              pending={create.isPending || update.isPending}
              onSubmit={(payload) =>
                businessId
                  ? update.mutate({ payload, next: 'location' })
                  : create.mutate(payload)
              }
            />
          ) : null}

          {businessId === null && step !== 'basics' && step !== 'personal' ? (
            <p className="text-ink-500">{t('wizard.saveBasicsFirst')}</p>
          ) : business.isLoading ? (
            <InlineSpinner />
          ) : (
            <>
              {step === 'location' && data ? (
                <LocationForm
                  serverError={update.error}
                  business={data}
                  submitLabel={t('wizard.saveAndContinue')}
                  pending={update.isPending}
                  onSubmit={(payload) => update.mutate({ payload, next: 'images' })}
                  footer={
                    <Button type="button" variant="ghost" onClick={() => setStep('basics')}>
                      {t('common.back')}
                    </Button>
                  }
                />
              ) : null}

              {step === 'images' && data ? (
                <div className="space-y-6">
                  <ImageManager business={data} />
                  <div className="flex gap-3 border-t border-ink-100 pt-5">
                    <Button size="lg" onClick={() => setStep('social')}>
                      {t('common.continue')}
                    </Button>
                    <Button variant="ghost" onClick={() => setStep('location')}>
                      {t('common.back')}
                    </Button>
                  </div>
                </div>
              ) : null}

              {step === 'social' && data ? (
                <SocialForm
                  serverError={update.error}
                  business={data}
                  submitLabel={t('wizard.saveAndContinue')}
                  pending={update.isPending}
                  onSubmit={(payload) => update.mutate({ payload, next: 'documents' })}
                  footer={
                    <Button type="button" variant="ghost" onClick={() => setStep('images')}>
                      {t('common.back')}
                    </Button>
                  }
                />
              ) : null}

              {step === 'documents' && data ? (
                <div className="space-y-6">
                  <DocumentManager business={data} />
                  <div className="flex gap-3 border-t border-ink-100 pt-5">
                    <Button size="lg" onClick={() => setStep('items')}>
                      {t('common.continue')}
                    </Button>
                    <Button variant="ghost" onClick={() => setStep('social')}>
                      {t('common.back')}
                    </Button>
                  </div>
                </div>
              ) : null}

              {step === 'items' && data ? (
                <div className="space-y-6">
                  <ItemManager businessId={data.id} />
                  <div className="flex gap-3 border-t border-ink-100 pt-5">
                    <Button size="lg" onClick={() => setStep('review')}>
                      {t('wizard.continueToReview')}
                    </Button>
                    <Button variant="ghost" onClick={() => setStep('documents')}>
                      {t('common.back')}
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
          {t('wizard.draftNotice')}{' '}
          <Link to="/dashboard" className="text-brand-700 hover:underline">
            {t('wizard.backToDashboard')}
          </Link>
        </p>
      ) : null}

      {/* Below the wizard rather than inside a step, so it is reachable from
          whichever step someone stalled on. */}
      <AssistedListing contextKey="assisted.contextWizard" />
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
  const t = useT()
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
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
          <PartyPopper className="h-7 w-7" aria-hidden="true" />
        </span>
        <h2 className="text-xl">{t('wizard.reviewTitle', { name })}</h2>
        <p className="mt-2 text-ink-500">{t('wizard.reviewBody')}</p>
      </div>

      {readiness.isLoading ? (
        <InlineSpinner label={t('wizard.checkingReadiness')} />
      ) : missing.length > 0 ? (
        <div className="rounded-xl border-2 border-sand-300 bg-sand-50 p-4">
          <p className="font-semibold text-clay-800">{t('wizard.missingTitle')}</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {missing.map((item) => (
              <li key={item}>
                {/* The API returns catalog keys, not sentences, so the
                    reader's locale decides the wording. */}
                <Badge className="bg-white text-clay-700">{t(item as TranslationKey)}</Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="rounded-xl border-2 border-olive-200 bg-olive-50 p-4 text-olive-800">
          {t('wizard.allComplete')}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button size="lg" disabled={!ready} loading={submitting} onClick={onSubmit}>
          <Send className="h-5 w-5" aria-hidden="true" />
          {t('dashboard.submitForReview')}
        </Button>
        <Button variant="ghost" onClick={onBack}>
          {t('common.back')}
        </Button>
      </div>
    </div>
  )
}
