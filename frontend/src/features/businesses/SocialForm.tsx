import { zodResolver } from '@hookform/resolvers/zod'
import { Facebook, Globe, Instagram, MessageCircle, Music2, Youtube } from 'lucide-react'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import type { BusinessPayload } from '@/services/api/endpoints'
import { useT, type TranslationKey } from '@/i18n'
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import type { OwnerBusiness, SocialPlatform } from '@/types/api'
import { socialLinksSchema, type SocialLinksValues } from '@/utils/validation'

interface SocialFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: Partial<BusinessPayload>) => void
  /** The parent's last save failure, so a 422 lands on the right input. */
  serverError?: unknown
  footer?: React.ReactNode
}

const FIELDS = [
  { key: 'instagram', platform: 'INSTAGRAM', labelKey: 'platform.INSTAGRAM', icon: Instagram, placeholder: 'instagram.com/username' },
  { key: 'facebook', platform: 'FACEBOOK', labelKey: 'platform.FACEBOOK', icon: Facebook, placeholder: 'facebook.com/page' },
  { key: 'tiktok', platform: 'TIKTOK', labelKey: 'platform.TIKTOK', icon: Music2, placeholder: 'tiktok.com/@username' },
  { key: 'youtube', platform: 'YOUTUBE', labelKey: 'platform.YOUTUBE', icon: Youtube, placeholder: 'youtube.com/@channel' },
  { key: 'whatsapp_url', platform: 'WHATSAPP', labelKey: 'form.whatsappUrl', icon: MessageCircle, placeholder: 'wa.me/9613123456' },
  { key: 'website', platform: 'WEBSITE', labelKey: 'platform.WEBSITE', icon: Globe, placeholder: 'https://example.com' },
] as const satisfies readonly {
  key: keyof SocialLinksValues
  platform: SocialPlatform
  labelKey: TranslationKey
  icon: typeof Instagram
  placeholder: string
}[]

/** All links optional — only the ones actually provided are rendered publicly. */
export function SocialForm({ business, submitLabel, pending, onSubmit, serverError, footer }: SocialFormProps) {
  const existing = new Map((business?.social_links ?? []).map((link) => [link.platform, link.url]))
  const t = useT()
  const schema = useMemo(() => socialLinksSchema(t), [t])

  const {
    register,
    handleSubmit,
    setError,
    getValues,
    formState: { errors },
  } = useForm<SocialLinksValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      instagram: existing.get('INSTAGRAM') ?? '',
      facebook: existing.get('FACEBOOK') ?? '',
      tiktok: existing.get('TIKTOK') ?? '',
      youtube: existing.get('YOUTUBE') ?? '',
      whatsapp_url: existing.get('WHATSAPP') ?? '',
      website: existing.get('WEBSITE') ?? '',
    },
  })

  useApplyServerFieldErrors(serverError, setError, getValues)

  const submit = handleSubmit((values) => {
    const social_links = FIELDS.flatMap(({ key, platform }) => {
      const url = values[key]?.trim()
      return url ? [{ platform, url }] : []
    })
    onSubmit({ social_links })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <p className="text-ink-500">{t('form.socialIntro')}</p>

      {FIELDS.map(({ key, labelKey, icon: Icon, placeholder }) => (
        <Field key={key} label={t(labelKey)} error={errors[key]?.message}>
          {(props) => (
            <div className="relative">
              <Icon className="pointer-events-none absolute inset-y-0 start-3.5 my-auto h-5 w-5 text-ink-300" aria-hidden="true" />
              <Input
                {...props}
                {...register(key)}
                type="url"
                dir="ltr"
                placeholder={placeholder}
                className="ltr-nums ps-11"
                invalid={Boolean(errors[key])}
              />
            </div>
          )}
        </Field>
      ))}

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" size="lg" loading={pending}>
          {submitLabel}
        </Button>
        {footer}
      </div>
    </form>
  )
}
