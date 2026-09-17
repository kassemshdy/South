import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, Download, ExternalLink, PauseCircle, PlayCircle, X } from 'lucide-react'
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
import { IssueCredentialsCard } from '@/features/admin/IssueCredentialsCard'
import { OwnerIdentityCard } from '@/features/admin/OwnerIdentityCard'
import { OWNER_RELATION_KEYS } from '@/features/businesses/labels'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDate, formatPrice, PLATFORM_KEYS, STATUS_KEYS } from '@/utils/format'
import { rejectSchema } from '@/utils/validation'

type RejectValues = z.infer<ReturnType<typeof rejectSchema>>
type ConfirmAction = 'approve' | 'reject' | 'suspend' | 'reactivate' | null

export function AdminReviewPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { t, locale } = useI18n()
  const [confirming, setConfirming] = useState<ConfirmAction>(null)
  const schema = useMemo(() => rejectSchema(t), [t])

  const business = useQuery({
    queryKey: queryKeys.adminBusiness(id),
    queryFn: () => adminApi.get(id),
    enabled: id.length > 0,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminBusiness(id) })
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
    mutationFn: () => adminApi.downloadVerificationDocument(business.data?.owner_id ?? ''),
    onSuccess: saveBlob,
    onError: onDownloadError,
  })

  const downloadCv = useMutation({
    mutationFn: () => adminApi.downloadCvDocument(business.data?.owner_id ?? ''),
    onSuccess: saveBlob,
    onError: onDownloadError,
  })

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

  if (business.isLoading) return <InlineSpinner />
  if (business.isError || !business.data) {
    return <ErrorState error={business.error} onRetry={() => void business.refetch()} />
  }

  const data = business.data

  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/admin/businesses" className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700">
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        {t('admin.backToBusinesses')}
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
              {t('admin.submittedAt', { date: formatDate(data.submitted_at, locale) })}
            </p>
          </div>
        </div>

        {data.status === 'APPROVED' ? (
          <Button asChild variant="outline" size="sm">
            <Link to={`/business/${encodeURIComponent(data.slug)}`}>
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
              {data.status === 'DRAFT'
                ? t('admin.draftNotice')
                : t('admin.rejectedNotice')}
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
              <Detail labelKey="admin.fieldShortDescription" value={data.short_description} />
              <Detail labelKey="admin.fieldDescription" value={data.description} />
              <Detail labelKey="admin.fieldCategory" value={data.category?.name_ar ?? null} />
              <Detail labelKey="admin.fieldLocation" value={data.location?.name_ar ?? null} />
              <Detail labelKey="admin.fieldAddress" value={data.address_text} />
              <Detail labelKey="admin.fieldPhone" value={data.phone} ltr />
              <Detail labelKey="admin.fieldWhatsapp" value={data.whatsapp} ltr />
              <Detail labelKey="admin.fieldEmail" value={data.email} ltr />
              <Detail labelKey="admin.fieldWebsite" value={data.website} ltr />
              <Detail labelKey="business.institutionLabel" value={data.institution_name} />
              <Detail
                labelKey="business.foundingDateLabel"
                value={data.founding_date ? formatDate(data.founding_date, locale) : null}
              />
              <Detail labelKey="business.productionLabel" value={data.production_nature} />
              <Detail
                labelKey="business.yearsOfExperienceLabel"
                value={data.years_of_experience !== null ? String(data.years_of_experience) : null}
                ltr
              />
              {/* Per business, not per account -- never on OwnerIdentityCard. */}
              <Detail
                labelKey="business.ownerRelationLabel"
                value={data.owner_relation ? t(OWNER_RELATION_KEYS[data.owner_relation]) : null}
              />
            </CardBody>
          </Card>

          {data.images.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">
                  {t('admin.galleryTitle', { count: data.images.length })}
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

          {data.items.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">
                  {t('admin.itemsTitle', { count: data.items.length })}
                </h2>
              </CardHeader>
              <CardBody>
                <ul className="divide-y divide-ink-100">
                  {data.items.map((item) => (
                    <li key={item.id} className="flex items-start justify-between gap-3 py-3">
                      <div>
                        <p className="font-semibold">{item.title}</p>
                        {item.description ? <p className="text-sm text-ink-500">{item.description}</p> : null}
                        {!item.is_available ? (
                          <p className="text-xs text-ink-500">{t('items.unavailable')}</p>
                        ) : null}
                      </div>
                      <span className="ltr-nums shrink-0 font-bold text-brand-800">
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
              <h2 className="font-bold">{t('admin.ownerTitle')}</h2>
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

          {/* Right where the approve button is, because handing over the
              login is the next thing that has to happen for an applicant who
              has no other way in. Still a separate press: see the card. */}
          <IssueCredentialsCard userId={data.owner_id} phoneNumber={data.owner_phone} />

          <OwnerIdentityCard identity={data.owner_identity} />

          {data.social_links.length > 0 ? (
            <Card>
              <CardHeader>
                <h2 className="font-bold">{t('admin.socialTitle')}</h2>
              </CardHeader>
              <CardBody className="space-y-2">
                {data.social_links.map((link) => (
                  <a
                    key={link.platform}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block truncate text-sm text-brand-700 hover:underline"
                  >
                    {t(PLATFORM_KEYS[link.platform])}:{' '}
                    <span className="ltr-nums">{link.url}</span>
                  </a>
                ))}
              </CardBody>
            </Card>
          ) : null}

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
                        <Badge className="bg-sand-100 text-brand-700">
                          {t(STATUS_KEYS[action.to_status])}
                        </Badge>
                        <span className="text-xs text-ink-300">
                          {formatDate(action.created_at, locale)}
                        </span>
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
          <DialogContent
            title={t('admin.confirmRejectTitle')}
            description={t('admin.confirmRejectBody', { name: data.name })}
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
                ? t('admin.confirmApproveBody', { name: data.name })
                : confirming === 'suspend'
                  ? t('admin.confirmSuspendBody', { name: data.name })
                  : t('admin.confirmReactivateBody', { name: data.name })
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
