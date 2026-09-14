import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronDown } from 'lucide-react'
import { useMemo } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useCategories } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import type { BusinessPayload } from '@/services/api/endpoints'
import type { OwnerBusiness } from '@/types/api'
import { businessBasicsSchema, type BusinessBasicsValues } from '@/utils/validation'

interface BasicsFormProps {
  business?: OwnerBusiness | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: BusinessPayload) => void
  /**
   * The last failure from the parent's save mutation. The parent owns the
   * mutation and this form owns the fields, so a 422's per-field sentences
   * have to travel back down to be shown on the input they are about.
   */
  serverError?: unknown
  footer?: React.ReactNode
}

/** Step 1 of the wizard, and the first tab of the edit screen. */
export function BasicsForm({
  business,
  submitLabel,
  pending,
  onSubmit,
  serverError,
  footer,
}: BasicsFormProps) {
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
    setError,
    getValues,
    formState: { errors },
  } = useForm<BusinessBasicsValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: business?.name ?? '',
      short_description: business?.short_description ?? '',
      description: business?.description ?? '',
      category_id: business?.category?.id ?? '',
      custom_category_text: business?.custom_category_text ?? '',
      institution_name: business?.institution_name ?? '',
      founding_date: business?.founding_date ?? '',
      production_nature: business?.production_nature ?? '',
      years_of_experience: business?.years_of_experience?.toString() ?? '',
      owner_relation: business?.owner_relation ?? '',
      phone: business?.phone ?? '',
      whatsapp: business?.whatsapp ?? '',
      email: business?.email ?? '',
      website: business?.website ?? '',
    },
  })

  const categoryId = useWatch({ control, name: 'category_id' })
  const isOtherCategory = Boolean(otherCategoryId) && categoryId === otherCategoryId

  useApplyServerFieldErrors(serverError, setError, getValues)

  const submit = handleSubmit((values) => {
    onSubmit({
      name: values.name,
      short_description: values.short_description || null,
      description: values.description || null,
      category_id: values.category_id || null,
      custom_category_text: values.custom_category_text || null,
      institution_name: values.institution_name || null,
      founding_date: values.founding_date || null,
      production_nature: values.production_nature || null,
      years_of_experience: values.years_of_experience ? Number(values.years_of_experience) : null,
      owner_relation: (values.owner_relation || null) as BusinessPayload['owner_relation'],
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

      {/* Nothing in here is required to get reviewed.
          The submission rules in `app/services/business.py` ask for six
          things: a name, a short description, a category, an area, a logo and
          one contact number. Everything else was sitting in the same flat
          column, which made a six-field form read as a twelve-field one to
          exactly the person least likely to push through it. Collapsed, and
          labelled as skippable, because it genuinely is — and a listing can
          be filled out further from the dashboard once it is live. */}
      <details className="group rounded-2xl border border-ink-100 bg-sand-50/50 [&_summary::-webkit-details-marker]:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-2xl p-4 text-start font-semibold text-ink-700 hover:bg-sand-100">
          <span>
            {t('form.optionalSectionTitle')}
            <span className="mt-0.5 block text-sm font-normal text-ink-500">
              {t('form.optionalSectionHint')}
            </span>
          </span>
          <ChevronDown
            className="h-5 w-5 shrink-0 text-ink-500 transition-transform group-open:rotate-180"
            aria-hidden="true"
          />
        </summary>

        <div className="space-y-5 border-t border-ink-100 p-4">
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

          <fieldset className="space-y-5 rounded-2xl border border-ink-100 p-4">
            <legend className="px-2 text-sm font-bold text-clay-700">
              {t('form.producerHeading')}
            </legend>
            <p className="text-sm text-ink-500">{t('form.producerHint')}</p>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t('form.institutionName')} error={errors.institution_name?.message}>
                {(props) => (
                  <Input
                    {...props}
                    {...register('institution_name')}
                    placeholder={t('form.institutionNamePlaceholder')}
                    invalid={Boolean(errors.institution_name)}
                  />
                )}
              </Field>

              <Field
                label={t('form.foundingDate')}
                error={errors.founding_date?.message}
                hint={t('form.foundingDateHint')}
              >
                {(props) => (
                  <Input
                    {...props}
                    {...register('founding_date')}
                    type="date"
                    dir="ltr"
                    className="ltr-nums"
                    invalid={Boolean(errors.founding_date)}
                  />
                )}
              </Field>
            </div>

            <Field
              label={t('form.productionNature')}
              error={errors.production_nature?.message}
              hint={t('form.productionNatureHint')}
            >
              {(props) => (
                <Textarea
                  {...props}
                  {...register('production_nature')}
                  rows={3}
                  placeholder={t('form.productionNaturePlaceholder')}
                  invalid={Boolean(errors.production_nature)}
                />
              )}
            </Field>

            <Field
              label={t('form.yearsOfExperience')}
              error={errors.years_of_experience?.message}
              hint={t('form.yearsOfExperienceHint')}
            >
              {(props) => (
                <Input
                  {...props}
                  {...register('years_of_experience')}
                  inputMode="numeric"
                  dir="ltr"
                  className="ltr-nums"
                  placeholder="10"
                  invalid={Boolean(errors.years_of_experience)}
                />
              )}
            </Field>
          </fieldset>

          {/* Not producer detail -- this answers a reviewer's question
              (is this person entitled to list on behalf of the place) and
              never reaches the public listing. See OwnerBusinessOut. */}
          <fieldset className="space-y-3 rounded-2xl border border-ink-100 p-4">
            <legend className="px-2 text-sm font-bold text-clay-700">
              {t('form.ownerRelationHeading')}
            </legend>

            <Field label={t('form.ownerRelationLabel')} error={errors.owner_relation?.message}>
              {(props) => (
                <Controller
                  control={control}
                  name="owner_relation"
                  render={({ field }) => (
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <SelectTrigger
                        id={props.id}
                        aria-describedby={props['aria-describedby']}
                        invalid={Boolean(errors.owner_relation)}
                      >
                        <SelectValue placeholder={t('form.ownerRelationPlaceholder')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="OWNER">{t('form.ownerRelationOwner')}</SelectItem>
                        <SelectItem value="MANAGER">{t('form.ownerRelationManager')}</SelectItem>
                        <SelectItem value="WORKER">{t('form.ownerRelationWorker')}</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              )}
            </Field>
          </fieldset>
        </div>
      </details>

      {/* Identity is set on the account, not here: one legal name per
          person, however many businesses they own. */}
      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        {t('form.identityMovedNote')}
      </p>

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
