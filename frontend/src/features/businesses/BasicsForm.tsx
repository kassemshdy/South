import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useCategories } from '@/hooks/useTaxonomy'
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

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<BusinessBasicsValues>({
    resolver: zodResolver(businessBasicsSchema),
    defaultValues: {
      name: business?.name ?? '',
      short_description: business?.short_description ?? '',
      description: business?.description ?? '',
      category_id: business?.category?.id ?? '',
      phone: business?.phone ?? '',
      whatsapp: business?.whatsapp ?? '',
      email: business?.email ?? '',
      website: business?.website ?? '',
    },
  })

  const submit = handleSubmit((values) => {
    onSubmit({
      name: values.name,
      short_description: values.short_description || null,
      description: values.description || null,
      category_id: values.category_id || null,
      phone: values.phone || null,
      whatsapp: values.whatsapp || null,
      email: values.email || null,
      website: values.website || null,
    })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Field label="اسم النشاط" required error={errors.name?.message}>
        {(props) => (
          <Input {...props} {...register('name')} placeholder="مثال: مناقيش الضيعة" invalid={Boolean(errors.name)} />
        )}
      </Field>

      <Field
        label="وصف مختصر"
        required
        error={errors.short_description?.message}
        hint="سطر واحد يظهر في بطاقة النشاط ونتائج البحث."
      >
        {(props) => (
          <Input
            {...props}
            {...register('short_description')}
            placeholder="مناقيش وفطائر على الصاج كل صباح"
            invalid={Boolean(errors.short_description)}
          />
        )}
      </Field>

      <Field label="نبذة عن النشاط" error={errors.description?.message}>
        {(props) => (
          <Textarea
            {...props}
            {...register('description')}
            rows={5}
            placeholder="اكتب عن نشاطك، ما يميّزه، وساعات العمل…"
            invalid={Boolean(errors.description)}
          />
        )}
      </Field>

      <Field label="التصنيف" required error={errors.category_id?.message}>
        {(props) => (
          <Controller
            control={control}
            name="category_id"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']} invalid={Boolean(errors.category_id)}>
                  <SelectValue placeholder="اختر تصنيفاً" />
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

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="رقم الهاتف للنشر" error={errors.phone?.message} hint="هذا الرقم يظهر للزوار.">
          {(props) => (
            <Input {...props} {...register('phone')} type="tel" dir="ltr" className="ltr-nums" placeholder="07740111" invalid={Boolean(errors.phone)} />
          )}
        </Field>

        <Field label="رقم واتساب" error={errors.whatsapp?.message} hint="يظهر كزر تواصل مباشر.">
          {(props) => (
            <Input {...props} {...register('whatsapp')} type="tel" dir="ltr" className="ltr-nums" placeholder="03123456" invalid={Boolean(errors.whatsapp)} />
          )}
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="البريد الإلكتروني" error={errors.email?.message}>
          {(props) => (
            <Input {...props} {...register('email')} type="email" dir="ltr" className="ltr-nums" invalid={Boolean(errors.email)} />
          )}
        </Field>

        <Field label="الموقع الإلكتروني" error={errors.website?.message}>
          {(props) => (
            <Input {...props} {...register('website')} type="url" dir="ltr" className="ltr-nums" placeholder="https://" invalid={Boolean(errors.website)} />
          )}
        </Field>
      </div>

      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        رقم هاتفك الذي سجّلت به لن يُنشر. تظهر للزوار فقط أرقام التواصل التي تدخلها هنا.
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
