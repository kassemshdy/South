import { useMutation } from '@tanstack/react-query'
import { Check, Handshake, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { Turnstile } from '@/components/ui/Turnstile'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { partnerApi, type PartnerPayload } from '@/services/api/endpoints'

type FieldKey = keyof PartnerPayload

const FIELDS: { key: FieldKey; labelKey: TranslationKey; multiline?: boolean; tel?: boolean }[] = [
  { key: 'name', labelKey: 'partner.nameLabel' },
  { key: 'phone', labelKey: 'partner.phoneLabel', tel: true },
  { key: 'occupation', labelKey: 'partner.occupationLabel' },
  { key: 'residence', labelKey: 'partner.residenceLabel' },
  { key: 'offer', labelKey: 'partner.offerLabel', multiline: true },
]

const EMPTY: PartnerPayload = { name: '', phone: '', occupation: '', residence: '', offer: '' }

/**
 * The partner form (round 3): someone who wants to support the project says
 * who they are and what they would offer, and it reaches an admin page of its
 * own. Anonymous, like a testimonial, so the server rate limits it and asks
 * for the captcha when one is configured.
 */
export function PartnerPage() {
  const t = useT()
  const toast = useToast()
  const [values, setValues] = useState<PartnerPayload>(EMPTY)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)

  useSeo({ title: `${t('partner.title')} | ${t('app.name')}`, description: t('partner.subtitle') })

  const send = useMutation({
    mutationFn: () => partnerApi.send(values, captchaToken),
    onError: (error) =>
      toast.error(t('partner.sendFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    send.mutate()
  }

  if (send.isSuccess) {
    return (
      <div className="container-page flex max-w-xl justify-center py-16">
        <Card className="w-full">
          <CardBody className="p-8 text-center">
            <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
            <h1 className="mt-4 text-2xl">{t('partner.sentTitle')}</h1>
            <p className="mt-2 text-ink-500">{send.data.message}</p>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="container-page max-w-2xl py-10">
      <header className="mb-6">
        <Handshake className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('partner.title')}</h1>
        <p className="mt-2 text-ink-500">{t('partner.subtitle')}</p>
      </header>

      <Card>
        <CardBody className="p-6">
          <form onSubmit={submit} className="space-y-5">
            {FIELDS.map((field) => (
              <Field key={field.key} label={t(field.labelKey)} required>
                {(props) =>
                  field.multiline ? (
                    <Textarea
                      {...props}
                      rows={5}
                      required
                      minLength={5}
                      maxLength={2000}
                      value={values[field.key]}
                      onChange={(event) =>
                        setValues((prev) => ({ ...prev, [field.key]: event.target.value }))
                      }
                    />
                  ) : (
                    <Input
                      {...props}
                      required
                      minLength={2}
                      maxLength={field.tel ? 20 : 200}
                      {...(field.tel
                        ? { type: 'tel', inputMode: 'tel' as const, dir: 'ltr' as const, autoComplete: 'tel' }
                        : {})}
                      value={values[field.key]}
                      onChange={(event) =>
                        setValues((prev) => ({ ...prev, [field.key]: event.target.value }))
                      }
                    />
                  )
                }
              </Field>
            ))}
            <Turnstile onToken={setCaptchaToken} />
            <Button type="submit" size="lg" loading={send.isPending}>
              <Send className="h-5 w-5" aria-hidden="true" />
              {t('partner.submit')}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
