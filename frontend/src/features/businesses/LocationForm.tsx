import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import type { BusinessPayload } from '@/services/api/endpoints'
import type { OwnerBusiness } from '@/types/api'
import { businessLocationSchema, type BusinessLocationValues } from '@/utils/validation'

interface LocationFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: Partial<BusinessPayload>) => void
  /** The parent's last save failure, so a 422 lands on the right input. */
  serverError?: unknown
  footer?: React.ReactNode
}

export function LocationForm({ business, submitLabel, pending, onSubmit, serverError, footer }: LocationFormProps) {
  const { groups } = useLocationGroups()
  const t = useT()
  const schema = useMemo(() => businessLocationSchema(t), [t])

  const {
    register,
    handleSubmit,
    control,
    setError,
    getValues,
    formState: { errors },
  } = useForm<BusinessLocationValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      location_id: business?.location?.id ?? '',
      address_text: business?.address_text ?? '',
      maps_url: business?.maps_url ?? '',
    },
  })

  useApplyServerFieldErrors(serverError, setError, getValues)

  const submit = handleSubmit((values) => {
    onSubmit({
      location_id: values.location_id || null,
      address_text: values.address_text || null,
      maps_url: values.maps_url || null,
    })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Field
        label={t('form.area')}
        required
        error={errors.location_id?.message}
        hint={t('form.areaHint')}
      >
        {(props) => (
          <Controller
            control={control}
            name="location_id"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']} invalid={Boolean(errors.location_id)}>
                  <SelectValue placeholder={t('form.areaPlaceholder')} />
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

      <Field
        label={t('form.address')}
        error={errors.address_text?.message}
        hint={t('form.addressHint')}
      >
        {(props) => (
          <Textarea {...props} {...register('address_text')} rows={3} invalid={Boolean(errors.address_text)} />
        )}
      </Field>

      <Field
        label={t('form.mapsUrl')}
        error={errors.maps_url?.message}
        hint={t('form.mapsUrlHint')}
      >
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
