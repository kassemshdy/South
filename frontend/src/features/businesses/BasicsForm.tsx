import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useCategories } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import type { BusinessPayload } from '@/services/api/endpoints'
import type { OwnerBusiness } from '@/types/api'
import { businessBasicsSchema, type BusinessBasicsValues } from '@/utils/validation'

interface BasicsFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: BusinessPayload) => void
  footer?: React.ReactNode
}

/** Step 1 of the wizard, and the first tab of the edit screen. */
export function BasicsForm({ business, submitLabel, pending, onSubmit, footer }: BasicsFormProps) {
  const categories = useCategories()
  const t = useT()
  const otherCategoryId = categories.data?.find((category) => category.slug === 'other')?.id
  // Rebuilt when the locale or the "Other" category id changes so validation
  // messages follow the UI and the conditional-required rule stays current.
  const schema = useMemo(() => businessBasicsSchema(t, otherCategoryId), [t, otherCategoryId])

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<BusinessBasicsValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: business?.name ?? '',
      short_description: business?.short_description ?? '',
      description: business?.description ?? '',
      category_id: business?.category?.id ?? '',
      custom_category_text: business?.custom_category_text ?? '',
      phone: business?.phone ?? '',
      whatsapp: business?.whatsapp ?? '',
      email: business?.email ?? '',
      website: business?.website ?? '',
    },
  })

  const categoryId = useWatch({ control, name: 'category_id' })
  const isOtherCategory = Boolean(otherCategoryId) && categoryId === otherCategoryId

  const submit = handleSubmit((values) => {
    onSubmit({
      name: values.name,
      short_description: values.short_description || null,
      description: values.description || null,
      category_id: values.category_id || null,
      custom_category_text: values.custom_category_text || null,
      phone: values.phone || null,
      whatsapp: values.whatsapp || null,
      email: values.email || null,
      website: values.website || null,
    })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Field label={t('form.name')} required error={errors.name?.message}>
        {(props) => (
          <Input {...props} {...register('name')} placeholder={t('form.namePlaceholder')} invalid={Boolean(errors.name)} />
        )}
      </Field>

      <Field
        label={t('form.shortDescription')}
        required
        error={errors.short_description?.message}
        hint={t('form.shortDescriptionHint')}
      >
        {(props) => (
          <Input
            {...props}
            {...register('short_description')}
            placeholder={t('form.shortDescriptionPlaceholder')}
            invalid={Boolean(errors.short_description)}
          />
        )}
      </Field>

      <Field label={t('form.description')} error={errors.description?.message}>
        {(props) => (
          <Textarea
            {...props}
            {...register('description')}
            rows={5}
            placeholder={t('form.descriptionPlaceholder')}
            invalid={Boolean(errors.description)}
          />
        )}
      </Field>

      <Field label={t('form.category')} required error={errors.category_id?.message}>
        {(props) => (
          <Controller
            control={control}
            name="category_id"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']} invalid={Boolean(errors.category_id)}>
                  <SelectValue placeholder={t('form.categoryPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {categories.data?.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name_ar}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        )}
      </Field>

      {isOtherCategory ? (
        <Field
          label={t('form.customCategoryLabel')}
          required
          error={errors.custom_category_text?.message}
        >
          {(props) => (
            <Input
              {...props}
              {...register('custom_category_text')}
              placeholder={t('form.customCategoryPlaceholder')}
              invalid={Boolean(errors.custom_category_text)}
            />
          )}
        </Field>
      ) : null}

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('form.phone')} error={errors.phone?.message} hint={t('form.phoneHint')}>
          {(props) => (
            <Input {...props} {...register('phone')} type="tel" dir="ltr" className="ltr-nums" placeholder="07740111" invalid={Boolean(errors.phone)} />
          )}
        </Field>

        <Field label={t('form.whatsapp')} error={errors.whatsapp?.message} hint={t('form.whatsappHint')}>
          {(props) => (
            <Input {...props} {...register('whatsapp')} type="tel" dir="ltr" className="ltr-nums" placeholder="03123456" invalid={Boolean(errors.whatsapp)} />
          )}
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('form.email')} error={errors.email?.message}>
          {(props) => (
            <Input {...props} {...register('email')} type="email" dir="ltr" className="ltr-nums" invalid={Boolean(errors.email)} />
          )}
        </Field>

        <Field label={t('form.website')} error={errors.website?.message}>
          {(props) => (
            <Input {...props} {...register('website')} type="url" dir="ltr" className="ltr-nums" placeholder="https://" invalid={Boolean(errors.website)} />
          )}
        </Field>
      </div>

      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        {t('form.privacyNote')}
      </p>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" size="lg" loading={pending}>
          {submitLabel}
        </Button>
        {footer}
      </div>
    </form>
  )
}
