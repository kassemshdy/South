import { zodResolver } from '@hookform/resolvers/zod'
import { Facebook, Globe, Instagram, MessageCircle, Music2, Youtube } from 'lucide-react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import type { BusinessPayload } from '@/services/api/endpoints'
import type { OwnerBusiness, SocialPlatform } from '@/types/api'
import { socialLinksSchema, type SocialLinksValues } from '@/utils/validation'

interface SocialFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: Partial<BusinessPayload>) => void
  footer?: React.ReactNode
}

const FIELDS = [
  { key: 'instagram', platform: 'INSTAGRAM', label: 'إنستغرام', icon: Instagram, placeholder: 'instagram.com/username' },
  { key: 'facebook', platform: 'FACEBOOK', label: 'فيسبوك', icon: Facebook, placeholder: 'facebook.com/page' },
  { key: 'tiktok', platform: 'TIKTOK', label: 'تيك توك', icon: Music2, placeholder: 'tiktok.com/@username' },
  { key: 'youtube', platform: 'YOUTUBE', label: 'يوتيوب', icon: Youtube, placeholder: 'youtube.com/@channel' },
  { key: 'whatsapp_url', platform: 'WHATSAPP', label: 'رابط واتساب', icon: MessageCircle, placeholder: 'wa.me/9613123456' },
  { key: 'website', platform: 'WEBSITE', label: 'الموقع الإلكتروني', icon: Globe, placeholder: 'https://example.com' },
] as const satisfies readonly {
  key: keyof SocialLinksValues
  platform: SocialPlatform
  label: string
  icon: typeof Instagram
  placeholder: string
}[]

/** All links optional — only the ones actually provided are rendered publicly. */
export function SocialForm({ business, submitLabel, pending, onSubmit, footer }: SocialFormProps) {
  const existing = new Map((business?.social_links ?? []).map((link) => [link.platform, link.url]))

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SocialLinksValues>({
    resolver: zodResolver(socialLinksSchema),
    defaultValues: {
      instagram: existing.get('INSTAGRAM') ?? '',
      facebook: existing.get('FACEBOOK') ?? '',
      tiktok: existing.get('TIKTOK') ?? '',
      youtube: existing.get('YOUTUBE') ?? '',
      whatsapp_url: existing.get('WHATSAPP') ?? '',
      website: existing.get('WEBSITE') ?? '',
    },
  })

  const submit = handleSubmit((values) => {
    const social_links = FIELDS.flatMap(({ key, platform }) => {
      const url = values[key]?.trim()
      return url ? [{ platform, url }] : []
    })
    onSubmit({ social_links })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <p className="text-ink-500">أضف الحسابات التي تريد عرضها فقط — الحقول الفارغة لن تظهر.</p>

      {FIELDS.map(({ key, label, icon: Icon, placeholder }) => (
        <Field key={key} label={label} error={errors[key]?.message}>
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
