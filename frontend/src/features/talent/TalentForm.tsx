import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useLocationGroups, useTalentSkills } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import type { TalentPayload } from '@/services/api/endpoints'
import type { OwnerTalent } from '@/types/api'
import { talentSchema, type TalentValues } from '@/utils/validation'

interface TalentFormProps {
  profile?: OwnerTalent | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: TalentPayload) => void
  footer?: React.ReactNode
}

/** The whole profile on one form — a talent profile is small enough not to
 * need the multi-step wizard a business listing gets. */
export function TalentForm({ profile, submitLabel, pending, onSubmit, footer }: TalentFormProps) {
  const skills = useTalentSkills()
  const { groups } = useLocationGroups()
  const t = useT()
  const otherSkillId = skills.data?.find((skill) => skill.slug === 'other')?.id
  const schema = useMemo(() => talentSchema(t, otherSkillId), [t, otherSkillId])

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<TalentValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: profile?.display_name ?? '',
      headline: profile?.headline ?? '',
      bio: profile?.bio ?? '',
      years_experience:
        profile?.years_experience !== null && profile?.years_experience !== undefined
          ? String(profile.years_experience)
          : '',
      skill_id: profile?.skill?.id ?? '',
      custom_skill_text: profile?.custom_skill_text ?? '',
      location_id: profile?.location?.id ?? '',
      phone: profile?.phone ?? '',
      whatsapp: profile?.whatsapp ?? '',
      email: profile?.email ?? '',
      website: profile?.website ?? '',
    },
  })

  const skillId = useWatch({ control, name: 'skill_id' })
  const isOtherSkill = Boolean(otherSkillId) && skillId === otherSkillId

  const submit = handleSubmit((values) => {
    onSubmit({
      display_name: values.display_name,
      headline: values.headline || null,
      bio: values.bio || null,
      years_experience: values.years_experience ? Number(values.years_experience) : null,
      skill_id: values.skill_id || null,
      custom_skill_text: values.custom_skill_text || null,
      location_id: values.location_id || null,
      phone: values.phone || null,
      whatsapp: values.whatsapp || null,
      email: values.email || null,
      website: values.website || null,
    })
  })

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Field
        label={t('talentForm.displayName')}
        required
        error={errors.display_name?.message}
        hint={t('talentForm.displayNameHint')}
      >
        {(props) => (
          <Input
            {...props}
            {...register('display_name')}
            placeholder={t('talentForm.displayNamePlaceholder')}
            invalid={Boolean(errors.display_name)}
          />
        )}
      </Field>

      <Field
        label={t('talentForm.headline')}
        required
        error={errors.headline?.message}
        hint={t('talentForm.headlineHint')}
      >
        {(props) => (
          <Input
            {...props}
            {...register('headline')}
            placeholder={t('talentForm.headlinePlaceholder')}
            invalid={Boolean(errors.headline)}
          />
        )}
      </Field>

      <Field label={t('talentForm.bio')} required error={errors.bio?.message}>
        {(props) => (
          <Textarea
            {...props}
            {...register('bio')}
            rows={6}
            placeholder={t('talentForm.bioPlaceholder')}
            invalid={Boolean(errors.bio)}
          />
        )}
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('talentForm.skill')} required error={errors.skill_id?.message}>
          {(props) => (
            <Controller
              control={control}
              name="skill_id"
              render={({ field }) => (
                <Select value={field.value || undefined} onValueChange={field.onChange}>
                  <SelectTrigger
                    id={props.id}
                    aria-describedby={props['aria-describedby']}
                    invalid={Boolean(errors.skill_id)}
                  >
                    <SelectValue placeholder={t('talentForm.skillPlaceholder')} />
                  </SelectTrigger>
                  <SelectContent>
                    {skills.data?.map((skill) => (
                      <SelectItem key={skill.id} value={skill.id}>
                        {skill.name_ar}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          )}
        </Field>

        <Field
          label={t('talentForm.yearsExperience')}
          error={errors.years_experience?.message}
        >
          {(props) => (
            <Input
              {...props}
              {...register('years_experience')}
              inputMode="numeric"
              dir="ltr"
              className="ltr-nums"
              placeholder="5"
              invalid={Boolean(errors.years_experience)}
            />
          )}
        </Field>
      </div>

      {isOtherSkill ? (
        <Field
          label={t('talentForm.customSkillLabel')}
          required
          error={errors.custom_skill_text?.message}
        >
          {(props) => (
            <Input
              {...props}
              {...register('custom_skill_text')}
              placeholder={t('talentForm.customSkillPlaceholder')}
              invalid={Boolean(errors.custom_skill_text)}
            />
          )}
        </Field>
      ) : null}

      <Field label={t('talentForm.location')} required error={errors.location_id?.message}>
        {(props) => (
          <Controller
            control={control}
            name="location_id"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger
                  id={props.id}
                  aria-describedby={props['aria-describedby']}
                  invalid={Boolean(errors.location_id)}
                >
                  <SelectValue placeholder={t('talentForm.locationPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {groups.map(({ district, towns }) => [
                    <SelectItem key={district.id} value={district.id}>
                      {district.name_ar}
                    </SelectItem>,
                    ...towns.map((town) => (
                      <SelectItem key={town.id} value={town.id}>
                        {'  '}
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

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('form.phone')} error={errors.phone?.message} hint={t('form.phoneHint')}>
          {(props) => (
            <Input
              {...props}
              {...register('phone')}
              type="tel"
              dir="ltr"
              className="ltr-nums"
              placeholder="07740111"
              invalid={Boolean(errors.phone)}
            />
          )}
        </Field>

        <Field
          label={t('form.whatsapp')}
          error={errors.whatsapp?.message}
          hint={t('form.whatsappHint')}
        >
          {(props) => (
            <Input
              {...props}
              {...register('whatsapp')}
              type="tel"
              dir="ltr"
              className="ltr-nums"
              placeholder="03123456"
              invalid={Boolean(errors.whatsapp)}
            />
          )}
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('form.email')} error={errors.email?.message}>
          {(props) => (
            <Input
              {...props}
              {...register('email')}
              type="email"
              dir="ltr"
              className="ltr-nums"
              invalid={Boolean(errors.email)}
            />
          )}
        </Field>

        <Field label={t('form.website')} error={errors.website?.message}>
          {(props) => (
            <Input
              {...props}
              {...register('website')}
              type="url"
              dir="ltr"
              className="ltr-nums"
              placeholder="https://"
              invalid={Boolean(errors.website)}
            />
          )}
        </Field>
      </div>

      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        {t('talentForm.privacyNote')}
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
