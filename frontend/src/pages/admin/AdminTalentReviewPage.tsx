import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Check,
  Download,
  ExternalLink,
  PauseCircle,
  PlayCircle,
  UserRound,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'
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
import { OwnerIdentityCard } from '@/features/admin/OwnerIdentityCard'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { PROFICIENCY_KEYS } from '@/features/talent/labels'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, STATUS_KEYS } from '@/utils/format'
import { rejectSchema } from '@/utils/validation'

type RejectValues = z.infer<ReturnType<typeof rejectSchema>>
type ConfirmAction = 'approve' | 'reject' | 'suspend' | 'reactivate' | null

export function AdminTalentReviewPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { t, locale } = useI18n()
  const [confirming, setConfirming] = useState<ConfirmAction>(null)
  const schema = useMemo(() => rejectSchema(t), [t])

  const talent = useQuery({
    queryKey: queryKeys.adminTalent(id),
    queryFn: () => adminApi.getTalent(id),
    enabled: id.length > 0,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminTalent(id) })
    void queryClient.invalidateQueries({ queryKey: ['admin'] })
  }

  const saveBlob = ({ blob, filename }: { blob: Blob; filename: string | null }) => {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename ?? 'document'
    link.click()
    URL.revokeObjectURL(url)
  }

  const onDownloadError = (error: unknown) =>
    toast.error(
      t('admin.downloadDocumentFailed'),
      error instanceof ApiError ? error.message : undefined,
    )

  const downloadDocument = useMutation({
    mutationFn: () => adminApi.downloadVerificationDocument(talent.data?.owner_id ?? ''),
    onSuccess: saveBlob,
    onError: onDownloadError,
  })

  const downloadCv = useMutation({
    mutationFn: () => adminApi.downloadCvDocument(talent.data?.owner_id ?? ''),
    onSuccess: saveBlob,
    onError: onDownloadError,
  })

  const act = useMutation({
    mutationFn: ({ action, reason }: { action: Exclude<ConfirmAction, null>; reason?: string }) => {
      switch (action) {
        case 'approve':
          return adminApi.approveTalent(id)
        case 'reject':
          return adminApi.rejectTalent(id, reason ?? '')
        case 'suspend':
          return adminApi.suspendTalent(id, reason)
        case 'reactivate':
          return adminApi.reactivateTalent(id)
      }
    },
    onSuccess: (result) => {
      invalidate()
      setConfirming(null)
      toast.success(t('admin.statusUpdated', { status: t(STATUS_KEYS[result.status]) }))
    },
    onError: (error) =>
      toast.error(t('admin.actionFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RejectValues>({ resolver: zodResolver(schema) })

  if (talent.isLoading) return <InlineSpinner />
  if (talent.isError || !talent.data) {
    return <ErrorState error={talent.error} onRetry={() => void talent.refetch()} />
  }

  const data = talent.data

  // A single Detail row rather than a chip list — the review page is a dense
  // read-through, and every other field here is one label + one value.
  const languages =
    data && data.languages.length > 0
      ? data.languages
          .map((language) => `${language.name} — ${t(PROFICIENCY_KEYS[language.proficiency])}`)
          .join('\n')
      : null

  return (
    <div className="max-w-4xl space-y-6">
      <Link
        to="/admin/talent"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-clay-600"
      >
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t('admin.backToTalent')}
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full bg-sand-100 text-sand-500">
            {data.photo_url ? (
              <img src={data.photo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <UserRound className="h-8 w-8" aria-hidden="true" />
            )}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl">{data.display_name}</h1>
              <StatusBadge status={data.status} />
            </div>
            <p className="mt-1 text-sm text-ink-500">
              {t('admin.submittedAt', { date: formatDate(data.submitted_at, locale) })}
            </p>
          </div>
        </div>

        {data.status === 'APPROVED' ? (
          <Button asChild variant="outline" size="sm">
            <Link to={`/talent/${encodeURIComponent(data.slug)}`}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.publicPage')}
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
                {t('admin.approve')}
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
                {t('admin.reject')}
              </Button>
            </>
          ) : null}

          {data.status === 'APPROVED' ? (
            <Button size="lg" variant="outline" onClick={() => setConfirming('suspend')}>
              <PauseCircle className="h-5 w-5" aria-hidden="true" />
              {t('admin.suspend')}
            </Button>
          ) : null}

          {data.status === 'SUSPENDED' ? (
            <Button size="lg" onClick={() => setConfirming('reactivate')}>
              <PlayCircle className="h-5 w-5" aria-hidden="true" />
              {t('admin.reactivate')}
            </Button>
          ) : null}

          {data.status === 'DRAFT' || data.status === 'REJECTED' ? (
            <p className="text-ink-500">
              {data.status === 'DRAFT' ? t('admin.draftNotice') : t('admin.rejectedNotice')}
            </p>
          ) : null}
        </CardBody>
      </Card>

      {data.rejection_reason ? (
        <Card className="border-clay-200">
          <CardBody>
            <p className="font-semibold text-clay-900">{t('admin.rejectionReasonTitle')}</p>
            <p className="mt-1 text-clay-700">{data.rejection_reason}</p>
          </CardBody>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="font-bold">{t('admin.infoTitle')}</h2>
            </CardHeader>
            <CardBody className="space-y-3">
              <Detail labelKey="admin.fieldHeadline" value={data.headline} />
              <Detail labelKey="admin.fieldBio" value={data.bio} />
              <Detail
                labelKey="admin.fieldSkill"
                value={data.custom_skill_text ?? data.skill?.name_ar ?? null}
              />
              <Detail labelKey="admin.fieldLocation" value={data.location?.name_ar ?? null} />
              <Detail
                labelKey="admin.fieldYearsExperience"
                value={data.years_experience !== null ? String(data.years_experience) : null}
                ltr
              />
              <Detail labelKey="admin.fieldPhone" value={data.phone} ltr />
              <Detail labelKey="admin.fieldWhatsapp" value={data.whatsapp} ltr />
              <Detail labelKey="admin.fieldEmail" value={data.email} ltr />
              <Detail labelKey="admin.fieldWebsite" value={data.website} ltr />
              <Detail labelKey="talent.degreeLabel" value={data.highest_degree} />
              <Detail labelKey="talent.specializationLabel" value={data.specialization} />
              <Detail labelKey="talent.universityLabel" value={data.university} />
              <Detail labelKey="talent.experienceLabel" value={data.experience} />
              <Detail labelKey="talent.skillsLabel" value={data.skills_text} />
              <Detail labelKey="talent.servicesLabel" value={data.services_offered} />
              <Detail labelKey="talent.languagesLabel" value={languages} />
            </CardBody>
          </Card>

          {data.images.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">
                  {t('admin.portfolioTitle', { count: data.images.length })}
                </h2>
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
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="font-bold">{t('admin.accountTitle')}</h2>
            </CardHeader>
            <CardBody className="space-y-3">
              <Detail labelKey="admin.ownerName" value={data.owner_display_name} />
              <Detail labelKey="admin.ownerAccount" value={data.owner_phone} ltr />
              <Detail labelKey="admin.ownerPersonalPhone" value={data.owner_personal_phone} ltr />
              <p className="text-xs text-ink-300">{t('admin.ownerPrivacyNote')}</p>
              {data.owner_has_verification_document ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  loading={downloadDocument.isPending}
                  onClick={() => downloadDocument.mutate()}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  {t('admin.downloadDocument')}
                </Button>
              ) : (
                <p className="text-sm text-ink-500">{t('admin.noDocument')}</p>
              )}

              {data.owner_has_cv_document ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  loading={downloadCv.isPending}
                  onClick={() => downloadCv.mutate()}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  {t('admin.downloadCv')}
                </Button>
              ) : (
                <p className="text-sm text-ink-500">{t('admin.noCv')}</p>
              )}
            </CardBody>
          </Card>

          <OwnerIdentityCard identity={data.owner_identity} />

          <Card>
            <CardHeader>
              <h2 className="font-bold">{t('admin.historyTitle')}</h2>
            </CardHeader>
            <CardBody>
              {data.moderation_actions.length === 0 ? (
                <p className="text-sm text-ink-500">{t('admin.historyEmpty')}</p>
              ) : (
                <ol className="space-y-3">
                  {data.moderation_actions.map((action) => (
                    <li key={action.id} className="border-s-2 border-ink-100 ps-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className="bg-sand-100 text-clay-700">
                          {t(STATUS_KEYS[action.to_status])}
                        </Badge>
                        <span className="text-xs text-ink-300">
                          {formatDate(action.created_at, locale)}
                        </span>
                      </div>
                      {action.reason ? (
                        <p className="mt-1 text-sm text-ink-500">{action.reason}</p>
                      ) : null}
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
          <DialogContent
            title={t('admin.confirmRejectTitle')}
            description={t('admin.confirmRejectBody', { name: data.display_name })}
          >
            <form
              onSubmit={handleSubmit(({ reason }) => act.mutate({ action: 'reject', reason }))}
              className="space-y-4"
              noValidate
            >
              <Field label={t('admin.rejectReasonLabel')} required error={errors.reason?.message}>
                {(props) => (
                  <Textarea
                    {...props}
                    {...register('reason')}
                    rows={4}
                    placeholder={t('admin.rejectReasonPlaceholder')}
                    invalid={Boolean(errors.reason)}
                    autoFocus
                  />
                )}
              </Field>
              <div className="flex gap-3">
                <Button type="submit" variant="danger" block loading={act.isPending}>
                  {t('admin.confirmReject')}
                </Button>
                <DialogClose asChild>
                  <Button type="button" variant="outline" block>
                    {t('common.cancel')}
                  </Button>
                </DialogClose>
              </div>
            </form>
          </DialogContent>
        ) : confirming !== null ? (
          <DialogContent
            title={
              confirming === 'approve'
                ? t('admin.confirmApproveTitle')
                : confirming === 'suspend'
                  ? t('admin.confirmSuspendTitle')
                  : t('admin.confirmReactivateTitle')
            }
            description={
              confirming === 'approve'
                ? t('admin.confirmApproveBody', { name: data.display_name })
                : confirming === 'suspend'
                  ? t('admin.confirmSuspendBody', { name: data.display_name })
                  : t('admin.confirmReactivateBody', { name: data.display_name })
            }
          >
            <div className="flex gap-3">
              <Button
                block
                variant={confirming === 'suspend' ? 'danger' : 'primary'}
                loading={act.isPending}
                onClick={() => act.mutate({ action: confirming })}
              >
                {t('common.confirm')}
              </Button>
              <DialogClose asChild>
                <Button variant="outline" block>
                  {t('common.cancel')}
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  )
}

function Detail({
  labelKey,
  value,
  ltr,
}: {
  labelKey: TranslationKey
  value: string | null
  ltr?: boolean
}) {
  const { t } = useI18n()
  return (
    <div>
      <p className="text-sm font-semibold text-ink-700">{t(labelKey)}</p>
      <p
        className={`mt-0.5 whitespace-pre-line ${value ? 'text-ink-900' : 'text-ink-300'} ${
          ltr ? 'ltr-nums' : ''
        }`}
      >
        {value || t('common.notSet')}
      </p>
    </div>
  )
}
