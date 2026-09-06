import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileCheck2, Loader2, ShieldCheck, Upload } from 'lucide-react'
import { useRef } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { InlineSpinner } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { authApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
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
        <DocumentCard />
      </div>
    </div>
  )
}

function ProfileCard({
  user,
  onSaved,
}: {
  user: { display_name: string | null; personal_phone_number: string | null }
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const toast = useToast()
  const schema = accountSchema(t)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AccountValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: user.display_name ?? '',
      personal_phone_number: user.personal_phone_number ?? '',
    },
  })

  const save = useMutation({
    mutationFn: (values: AccountValues) =>
      authApi.updateProfile({
        display_name: values.display_name || null,
        personal_phone_number: values.personal_phone_number || null,
      }),
    onSuccess: async () => {
      await onSaved()
      toast.success(t('account.profileSaved'))
    },
    onError: (error) =>
      toast.error(t('account.profileSaveFailed'), error instanceof ApiError ? error.message : undefined),
  })

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
          <Button type="submit" loading={save.isPending}>
            {t('account.saveProfile')}
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}

function DocumentCard() {
  const t = useT()
  const { locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const documentQuery = useQuery({
    queryKey: queryKeys.myVerificationDocument,
    queryFn: authApi.getVerificationDocument,
  })

  const upload = useMutation({
    mutationFn: (file: File) => authApi.uploadVerificationDocument(file),
    onSuccess: () => {
      toast.success(t('account.documentUpload'))
      void queryClient.invalidateQueries({ queryKey: queryKeys.myVerificationDocument })
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
          <ShieldCheck className="h-5 w-5 text-clay-600" aria-hidden="true" />
          {t('account.documentTitle')}
        </h2>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-ink-500">{t('account.documentHint')}</p>

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
