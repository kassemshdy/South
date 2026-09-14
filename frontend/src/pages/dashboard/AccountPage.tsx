import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileCheck2, FileText, Loader2, ShieldCheck, Upload } from 'lucide-react'
import { useRef, type ReactNode } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import {
  GENDERS,
  GENDER_KEYS,
  MARITAL_STATUSES,
  MARITAL_STATUS_KEYS,
} from '@/features/identity/labels'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT, type TranslationKey } from '@/i18n'
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { User, VerificationDocument } from '@/types/api'
import { formatDate } from '@/utils/format'
import { accountSchema, type AccountValues } from '@/utils/validation'

const ACCEPTED_DOCUMENT_TYPES = 'application/pdf,image/jpeg,image/png'
const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

/**
 * Private account details — a separate page from any one business, since a
 * personal phone number and identity document belong to the owner, not to a
 * single listing.
 */
export function AccountPage() {
  const { user, refresh } = useAuth()
  const t = useT()
  useSeo({ title: t('account.seoTitle'), noIndex: true })

  if (!user) return <InlineSpinner />

  return (
    <div className="container-page max-w-2xl py-10">
      <header className="mb-8">
        <h1 className="text-3xl">{t('account.heading')}</h1>
        <p className="mt-2 text-ink-500">{t('account.subtitle')}</p>
      </header>

      <div className="space-y-6">
        <ProfileCard user={user} onSaved={refresh} />
        <DocumentCard
          icon={<ShieldCheck className="h-5 w-5 text-brand-700" aria-hidden="true" />}
          titleKey="account.documentTitle"
          hintKey="account.documentHint"
          queryKey={queryKeys.myVerificationDocument}
          read={authApi.getVerificationDocument}
          upload={authApi.uploadVerificationDocument}
        />
        <DocumentCard
          icon={<FileText className="h-5 w-5 text-brand-700" aria-hidden="true" />}
          titleKey="account.cvTitle"
          hintKey="account.cvHint"
          queryKey={queryKeys.myCvDocument}
          read={authApi.getCvDocument}
          upload={authApi.uploadCvDocument}
        />
      </div>
    </div>
  )
}

function ProfileCard({ user, onSaved }: { user: User; onSaved: () => Promise<void> }) {
  const t = useT()
  const toast = useToast()
  const schema = accountSchema(t)

  const {
    register,
    handleSubmit,
    control,
    setError,
    getValues,
    formState: { errors },
  } = useForm<AccountValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: user.display_name ?? '',
      personal_phone_number: user.personal_phone_number ?? '',
      full_name: user.full_name ?? '',
      birth_year: user.birth_year !== null ? String(user.birth_year) : '',
      gender: user.gender ?? '',
      marital_status: user.marital_status ?? '',
      registration_place: user.registration_place ?? '',
      residence_place: user.residence_place ?? '',
    },
  })

  const save = useMutation({
    mutationFn: (values: AccountValues) =>
      authApi.updateProfile({
        display_name: values.display_name || null,
        personal_phone_number: values.personal_phone_number || null,
        full_name: values.full_name || null,
        birth_year: values.birth_year ? Number(values.birth_year) : null,
        gender: values.gender || null,
        marital_status: values.marital_status || null,
        registration_place: values.registration_place || null,
        residence_place: values.residence_place || null,
      }),
    onSuccess: async () => {
      await onSaved()
      toast.success(t('account.profileSaved'))
    },
    onError: (error) =>
      toast.error(t('account.profileSaveFailed'), error instanceof ApiError ? error.message : undefined),
  })

  // A 422 here is the identity block: eight fields, and the envelope alone
  // ("check the fields below") named none of them.
  useApplyServerFieldErrors(save.error, setError, getValues)

  const submit = handleSubmit((values) => save.mutate(values))

  return (
    <Card>
      <CardHeader>
        <h2 className="font-bold">{t('account.profileTitle')}</h2>
      </CardHeader>
      <CardBody>
        <form onSubmit={submit} className="space-y-5" noValidate>
          <Field
            label={t('account.displayNameLabel')}
            error={errors.display_name?.message}
            hint={t('account.displayNameHint')}
          >
            {(props) => (
              <Input
                {...props}
                {...register('display_name')}
                autoComplete="name"
                invalid={Boolean(errors.display_name)}
              />
            )}
          </Field>
          <Field
            label={t('account.personalPhoneLabel')}
            error={errors.personal_phone_number?.message}
            hint={t('account.personalPhoneHint')}
          >
            {(props) => (
              <Input
                {...props}
                {...register('personal_phone_number')}
                type="tel"
                dir="ltr"
                className="ltr-nums"
                placeholder="03123456"
                invalid={Boolean(errors.personal_phone_number)}
              />
            )}
          </Field>

          {/* Identity: one copy per account, shared by every listing it owns
              and shown to no visitor. */}
          <fieldset className="space-y-5 border-t border-ink-100 pt-5">
            <legend className="sr-only">{t('account.identityTitle')}</legend>
            <div>
              <h3 className="font-bold">{t('account.identityTitle')}</h3>
              <p className="mt-1 text-sm text-ink-500">{t('account.identityHint')}</p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t('account.fullNameLabel')} error={errors.full_name?.message}>
                {(props) => (
                  <Input
                    {...props}
                    {...register('full_name')}
                    invalid={Boolean(errors.full_name)}
                  />
                )}
              </Field>

              <Field
                label={t('account.birthYearLabel')}
                error={errors.birth_year?.message}
                hint={t('account.birthYearHint')}
              >
                {(props) => (
                  <Input
                    {...props}
                    {...register('birth_year')}
                    inputMode="numeric"
                    dir="ltr"
                    placeholder="1994"
                    className="ltr-nums"
                    invalid={Boolean(errors.birth_year)}
                  />
                )}
              </Field>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t('account.genderLabel')}>
                {(props) => (
                  <Controller
                    control={control}
                    name="gender"
                    render={({ field }) => (
                      <Select value={field.value || ''} onValueChange={field.onChange}>
                        <SelectTrigger id={props.id}>
                          <SelectValue placeholder={t('account.notSpecified')} />
                        </SelectTrigger>
                        <SelectContent>
                          {GENDERS.map((value) => (
                            <SelectItem key={value} value={value}>
                              {t(GENDER_KEYS[value])}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                )}
              </Field>

              <Field label={t('account.maritalStatusLabel')}>
                {(props) => (
                  <Controller
                    control={control}
                    name="marital_status"
                    render={({ field }) => (
                      <Select value={field.value || ''} onValueChange={field.onChange}>
                        <SelectTrigger id={props.id}>
                          <SelectValue placeholder={t('account.notSpecified')} />
                        </SelectTrigger>
                        <SelectContent>
                          {MARITAL_STATUSES.map((value) => (
                            <SelectItem key={value} value={value}>
                              {t(MARITAL_STATUS_KEYS[value])}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                )}
              </Field>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                label={t('account.registrationPlaceLabel')}
                error={errors.registration_place?.message}
              >
                {(props) => <Input {...props} {...register('registration_place')} />}
              </Field>
              <Field
                label={t('account.residencePlaceLabel')}
                error={errors.residence_place?.message}
              >
                {(props) => <Input {...props} {...register('residence_place')} />}
              </Field>
            </div>
          </fieldset>

          <Button type="submit" loading={save.isPending}>
            {t('account.saveProfile')}
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}

/**
 * One personal document — the ID scan or the CV. Both are uploaded, replaced
 * and stored identically and differ only in copy and endpoint, so they share
 * a card rather than two near-identical ones drifting apart.
 */
function DocumentCard({
  icon,
  titleKey,
  hintKey,
  queryKey,
  read,
  upload: uploadFile,
}: {
  icon: ReactNode
  titleKey: TranslationKey
  hintKey: TranslationKey
  queryKey: readonly string[]
  read: () => Promise<VerificationDocument | null>
  upload: (file: File) => Promise<VerificationDocument>
}) {
  const t = useT()
  const { locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const documentQuery = useQuery({
    queryKey,
    queryFn: read,
  })

  const upload = useMutation({
    mutationFn: (file: File) => uploadFile(file),
    onSuccess: () => {
      toast.success(t('account.documentUpload'))
      void queryClient.invalidateQueries({ queryKey })
    },
    onError: (error) =>
      toast.error(t('account.documentUploadFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const handleFile = (file: File | undefined) => {
    if (!file) return
    const acceptedTypes = ACCEPTED_DOCUMENT_TYPES.split(',')
    if (!acceptedTypes.includes(file.type)) {
      toast.error(t('account.badDocumentType'), t('account.badDocumentTypeDescription'))
      return
    }
    if (file.size > MAX_DOCUMENT_BYTES) {
      toast.error(t('account.documentTooLarge'), t('account.documentTooLargeDescription'))
      return
    }
    upload.mutate(file)
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="flex items-center gap-2 font-bold">
          {icon}
          {t(titleKey)}
        </h2>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-ink-500">{t(hintKey)}</p>

        {documentQuery.isLoading ? (
          <InlineSpinner />
        ) : documentQuery.data ? (
          <div className="flex items-center gap-2 rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
            <FileCheck2 className="h-5 w-5 shrink-0" aria-hidden="true" />
            {t('account.documentUploaded', { date: formatDate(documentQuery.data.created_at, locale) })}
          </div>
        ) : (
          <p className="rounded-xl border-2 border-dashed border-ink-100 p-4 text-center text-ink-500">
            {t('account.documentNone')}
          </p>
        )}

        <input
          ref={inputRef}
          type="file"
          // Named so a test (or a screen reader) can tell the two cards'
          // inputs apart; both are visually hidden behind their own button.
          aria-label={t(titleKey)}
          accept={ACCEPTED_DOCUMENT_TYPES}
          className="sr-only"
          onChange={(event) => {
            handleFile(event.target.files?.[0])
            event.target.value = ''
          }}
        />
        <Button
          type="button"
          variant="outline"
          disabled={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {upload.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              {t('account.documentUploading')}
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" aria-hidden="true" />
              {documentQuery.data ? t('account.documentReplace') : t('account.documentUpload')}
            </>
          )}
        </Button>
      </CardBody>
    </Card>
  )
}
