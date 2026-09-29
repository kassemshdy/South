import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { SiteSettings } from '@/types/api'

/**
 * The site's own contact details and social accounts, shown in the header,
 * the footer and on /contact. A field left empty is not shown anywhere.
 *
 * Every label is the one the public site already uses for the same thing, so
 * the admin reads the same words a visitor will.
 */
const FIELDS: {
  key: keyof SiteSettings
  labelKey: TranslationKey
  // 'text' for the links: a browser's own url check refuses facebook.com/…
  // without a scheme, which the server adds itself.
  type: 'tel' | 'email' | 'text'
  placeholder: string
}[] = [
  {
    key: 'contact_phone',
    labelKey: 'contactChannel.PHONE',
    type: 'tel',
    placeholder: '+961 …',
  },
  {
    key: 'contact_whatsapp',
    labelKey: 'platform.WHATSAPP',
    type: 'tel',
    placeholder: '+961 …',
  },
  {
    key: 'contact_email',
    labelKey: 'contactChannel.EMAIL',
    type: 'email',
    placeholder: '@',
  },
  {
    key: 'social_facebook',
    labelKey: 'platform.FACEBOOK',
    type: 'text',
    placeholder: 'https://facebook.com/…',
  },
  {
    key: 'social_instagram',
    labelKey: 'platform.INSTAGRAM',
    type: 'text',
    placeholder: 'https://instagram.com/…',
  },
]

const EMPTY: SiteSettings = {
  contact_phone: null,
  contact_whatsapp: null,
  contact_email: null,
  social_facebook: null,
  social_instagram: null,
}

export function AdminSiteSettingsPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const current = useQuery({
    queryKey: queryKeys.adminSiteSettings,
    queryFn: adminApi.siteSettings,
  })
  const [values, setValues] = useState<SiteSettings>(EMPTY)

  useEffect(() => {
    if (current.data) setValues(current.data)
  }, [current.data])

  const save = useMutation({
    mutationFn: adminApi.updateSiteSettings,
    onSuccess: (saved) => {
      setValues(saved)
      queryClient.setQueryData(queryKeys.adminSiteSettings, saved)
      // The header and footer read the public copy; refresh it too.
      void queryClient.invalidateQueries({ queryKey: queryKeys.siteSettings })
      toast.success(t('wizard.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(values)
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-3xl">{t('nav.contact')}</h1>

      {current.isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : current.isError ? (
        <ErrorState error={current.error} onRetry={() => void current.refetch()} />
      ) : (
        <Card>
          <CardBody>
            <form onSubmit={submit} className="space-y-5">
              {FIELDS.map((field) => (
                <Field key={field.key} label={t(field.labelKey)}>
                  {(props) => (
                    <Input
                      {...props}
                      type={field.type}
                      dir="ltr"
                      value={values[field.key] ?? ''}
                      placeholder={field.placeholder}
                      onChange={(event) =>
                        setValues((prev) => ({
                          ...prev,
                          [field.key]: event.target.value || null,
                        }))
                      }
                    />
                  )}
                </Field>
              ))}
              <Button type="submit" disabled={save.isPending}>
                {t('common.save')}
              </Button>
            </form>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
