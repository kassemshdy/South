import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import type { BusinessPayload } from '@/services/api/endpoints'
import type { OwnerBusiness } from '@/types/api'
import { businessLocationSchema, type BusinessLocationValues } from '@/utils/validation'

interface LocationFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: Partial<BusinessPayload>) => void
  footer?: React.ReactNode
}

export function LocationForm({ business, submitLabel, pending, onSubmit, footer }: LocationFormProps) {
  const { groups } = useLocationGroups()

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<BusinessLocationValues>({
    resolver: zodResolver(businessLocationSchema),
    defaultValues: {
      location_id: business?.location?.id ?? '',
      address_text: business?.address_text ?? '',
      maps_url: business?.maps_url ?? '',
    },
  })

  const submit = handleSubmit((values) => {
    onSubmit({
      location_id: values.location_id || null,
      address_text: values.address_text || null,
      maps_url: values.maps_url || null,
    })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Field label="المنطقة" required error={errors.location_id?.message} hint="اختر القضاء أو البلدة الأقرب لنشاطك.">
        {(props) => (
          <Controller
            control={control}
            name="location_id"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']} invalid={Boolean(errors.location_id)}>
                  <SelectValue placeholder="اختر المنطقة" />
                </SelectTrigger>
                <SelectContent>
                  {groups.map(({ district, towns }) => [
                    <SelectItem key={district.id} value={district.id}>
                      {district.name_ar}
                    </SelectItem>,
                    ...towns.map((town) => (
                      <SelectItem key={town.id} value={town.id}>
                        {'— '}
                        {town.name_ar}
                      </SelectItem>
                    )),
                  ])}
                </SelectContent>
              </Select>
            )}
          />
        )}
      </Field>

      <Field label="تفاصيل العنوان" error={errors.address_text?.message} hint="مثال: شارع البلدية، مقابل الحديقة العامة.">
        {(props) => (
          <Textarea {...props} {...register('address_text')} rows={3} invalid={Boolean(errors.address_text)} />
        )}
      </Field>

      <Field label="رابط الموقع على الخرائط" error={errors.maps_url?.message} hint="انسخ الرابط من تطبيق خرائط جوجل.">
        {(props) => (
          <Input {...props} {...register('maps_url')} type="url" dir="ltr" className="ltr-nums" placeholder="https://maps.google.com/…" invalid={Boolean(errors.maps_url)} />
        )}
      </Field>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" size="lg" loading={pending}>
          {submitLabel}
        </Button>
        {footer}
      </div>
    </form>
  )
}
