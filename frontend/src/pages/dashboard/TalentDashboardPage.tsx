import * as Tabs from '@radix-ui/react-tabs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowRight, ExternalLink, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { ErrorState, InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { LiveSharePanel } from '@/features/insights/LiveSharePanel'
import { ViewsPanel } from '@/features/insights/ViewsPanel'
import { OwnerServiceRequests } from '@/features/talent/OwnerServiceRequests'
import { TalentForm } from '@/features/talent/TalentForm'
import { TalentImageManager } from '@/features/talent/TalentImageManager'
import { OfferSwitcher } from '@/features/onboarding/OfferSwitcher'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { insightsApi, ownerTalentApi, type TalentPayload } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * The owner's own talent profile.
 *
 * One page rather than a create/edit pair: a profile is one-per-account, so
 * whether the caller has one is a 200-vs-404 on a single endpoint, not a route
 * decision the client has to make.
 */
export function TalentDashboardPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  // Opens on the photo tab while there is no photo. Submitting for review
  // *requires* one (see the readiness rules the submit endpoint enforces), so
  // a profile that lands on "details" sends someone through the whole form
  // only to be refused at the end for a field no screen had offered them.
  const [tab, setTab] = useState<string | null>(null)

  useSeo({ title: t('talentDashboard.seoTitle'), noIndex: true })

  const profile = useQuery({
    queryKey: queryKeys.myTalent,
    queryFn: ownerTalentApi.get,
    // A 404 here means "no profile yet", which is a normal state for a new
    // account — retrying it just delays the create form.
    retry: false,
  })

  // Hooks cannot sit below the early returns further down, so the counts
  // are fetched here and read after the profile is known to exist.
  const views = useQuery({ queryKey: queryKeys.myViews, queryFn: insightsApi.myViews })
  const readiness = useQuery({
    queryKey: queryKeys.myTalentReadiness,
    queryFn: ownerTalentApi.readiness,
    enabled: Boolean(profile.data),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myTalent })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myTalentReadiness })
  }

  const create = useMutation({
    mutationFn: (payload: TalentPayload) => ownerTalentApi.create(payload),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.myTalent, result)
      invalidate()
      toast.success(t('talentDashboard.created'), t('talentDashboard.createdDescription'))
    },
    onError: (error) =>
      toast.error(
        t('talentDashboard.createFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const save = useMutation({
    mutationFn: (payload: Partial<TalentPayload>) => ownerTalentApi.update(payload),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.myTalent, result)
      invalidate()
      toast.success(t('edit.saved'))
    },
    onError: (error) =>
      toast.error(t('edit.saveFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = useMutation({
    mutationFn: () => ownerTalentApi.submit(),
    onSuccess: () => {
      invalidate()
      toast.success(t('dashboard.submitted'), t('dashboard.submittedDescription'))
    },
    onError: (error) =>
      toast.error(
        t('dashboard.submitBlocked'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const remove = useMutation({
    mutationFn: () => ownerTalentApi.remove(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: queryKeys.myTalent })
      invalidate()
      toast.success(t('talentDashboard.deleted'))
    },
    onError: (error) =>
      toast.error(t('edit.deleteFailed'), error instanceof ApiError ? error.message : undefined),
  })

  if (profile.isLoading) return <InlineSpinner />

  // 404 is the "you don't have one yet" signal; anything else is a real error.
  const notFound = profile.error instanceof ApiError && profile.error.status === 404
  if (profile.isError && !notFound) {
    return (
      <div className="container-page py-16">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    )
  }

  const data = profile.data

  if (!data) {
    return (
      <div className="container-page max-w-3xl py-10">
        <BackLink />
        <header className="mb-6">
          <h1 className="text-3xl">{t('talentDashboard.createHeading')}</h1>
          <p className="mt-2 text-ink-500">{t('talentDashboard.createIntro')}</p>
        </header>

        {/* The counterpart of the wizard's, and unconditional here: nothing
            has been written yet, so there is nothing to strand. Only on the
            create form — once a profile exists this is the page for managing
            it, not a fork. */}
        <OfferSwitcher current="talent" />
        <Card>
          <CardBody>
            <TalentForm
            serverError={create.error ?? save.error}
              submitLabel={t('talentDashboard.createSubmit')}
              pending={create.isPending}
              onSubmit={(payload) => create.mutate(payload)}
            />
          </CardBody>
        </Card>
      </div>
    )
  }

  const canSubmit = data.status === 'DRAFT' || data.status === 'REJECTED'
  const missing = readiness.data ?? []

  return (
    <div className="container-page max-w-3xl py-10">
      <BackLink />

      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl">{data.display_name}</h1>
            <StatusBadge status={data.status} />
          </div>
          {data.status === 'APPROVED' ? (
            <p className="mt-1.5">
              <Link
                to={`/talent/${encodeURIComponent(data.slug)}`}
                className="inline-flex items-center gap-1.5 text-sm text-brand-700 hover:underline"
              >
                <ExternalLink className="h-4 w-4" aria-hidden="true" />
                {t('talentDashboard.viewPublic')}
              </Link>
            </p>
          ) : null}
        </div>

        {canSubmit ? (
          <Button loading={submit.isPending} onClick={() => submit.mutate()}>
            <Send className="h-4 w-4" aria-hidden="true" />
            {t('dashboard.submitForReview')}
          </Button>
        ) : null}
      </header>

      {data.status === 'APPROVED' ? (
        <>
          <LiveSharePanel
            name={data.display_name}
            path={`/talent/${encodeURIComponent(data.slug)}`}
          />
          <ViewsPanel
            views={views.data?.listings.find((entry) => entry.subject_id === data.id)}
            windowDays={views.data?.window_days ?? 14}
          />
        </>
      ) : null}

      {data.status === 'REJECTED' && data.rejection_reason ? (
        <div className="mb-6 flex gap-2.5 rounded-xl border-2 border-clay-200 bg-clay-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
          <div>
            <p className="font-semibold text-clay-900">{t('dashboard.needsChanges')}</p>
            <p className="mt-0.5 leading-relaxed text-clay-700">{data.rejection_reason}</p>
            <p className="mt-2 text-sm text-clay-700">{t('edit.rejectionHint')}</p>
          </div>
        </div>
      ) : null}

      {canSubmit && missing.length > 0 ? (
        <div className="mb-6 rounded-xl border-2 border-sand-300 bg-sand-50 p-4">
          <p className="font-semibold text-clay-900">{t('talentDashboard.missingHeading')}</p>
          <ul className="mt-2 list-inside list-disc text-clay-700">
            {missing.map((key) => (
              <li key={key}>{t(key as TranslationKey)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <Card>
        <Tabs.Root
          value={tab ?? (data.photo_url ? 'details' : 'images')}
          onValueChange={setTab}
        >
          <Tabs.List
            className="flex gap-1 overflow-x-auto border-b border-ink-100 p-2"
            aria-label={t('talentDashboard.tabsAria')}
          >
            <TabTrigger value="details">{t('talentDashboard.tabDetails')}</TabTrigger>
            <TabTrigger value="images">{t('talentDashboard.tabImages')}</TabTrigger>
            <TabTrigger value="requests">{t('serviceRequests.ownerTab')}</TabTrigger>
          </Tabs.List>

          <CardBody>
            <Tabs.Content value="details">
              <TalentForm
            serverError={create.error ?? save.error}
                profile={data}
                submitLabel={t('edit.saveChanges')}
                pending={save.isPending}
                onSubmit={(payload) => save.mutate(payload)}
                footer={
                  <Button
                    type="button"
                    variant="ghost"
                    loading={remove.isPending}
                    onClick={() => {
                      if (window.confirm(t('talentDashboard.deleteConfirm'))) remove.mutate()
                    }}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    {t('talentDashboard.delete')}
                  </Button>
                }
              />
            </Tabs.Content>

            <Tabs.Content value="images">
              <TalentImageManager profile={data} />
            </Tabs.Content>

            <Tabs.Content value="requests">
              <OwnerServiceRequests />
            </Tabs.Content>
          </CardBody>
        </Tabs.Root>
      </Card>
    </div>
  )
}

function BackLink() {
  const t = useT()
  return (
    <Link
      to="/dashboard"
      className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700"
    >
      <ArrowRight className="h-4 w-4" aria-hidden="true" />
      {t('wizard.backToDashboard')}
    </Link>
  )
}

function TabTrigger({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <Tabs.Trigger
      value={value}
      className="shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-ink-500 transition-colors hover:text-brand-700 data-[state=active]:bg-sand-100 data-[state=active]:text-brand-800"
    >
      {children}
    </Tabs.Trigger>
  )
}
