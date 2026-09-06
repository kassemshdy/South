import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Trash2 } from 'lucide-react'
import { useMemo } from 'react'
import { Controller, useFieldArray, useForm, useWatch } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useLocationGroups, useTalentSkills } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import type { TalentPayload } from '@/services/api/endpoints'
import type { OwnerTalent } from '@/types/api'
import { talentSchema, type TalentValues } from '@/utils/validation'

import {
  GENDERS,
  GENDER_KEYS,
  LANGUAGE_PROFICIENCIES,
  MARITAL_STATUSES,
  MARITAL_STATUS_KEYS,
  PROFICIENCY_KEYS,
} from './labels'

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
      highest_degree: profile?.highest_degree ?? '',
      specialization: profile?.specialization ?? '',
      university: profile?.university ?? '',
      experience: profile?.experience ?? '',
      skills_text: profile?.skills_text ?? '',
      services_offered: profile?.services_offered ?? '',
      languages:
        profile?.languages?.map((language) => ({
          name: language.name,
          proficiency: language.proficiency,
        })) ?? [],
      full_name: profile?.full_name ?? '',
      birth_year:
        profile?.birth_year !== null && profile?.birth_year !== undefined
          ? String(profile.birth_year)
          : '',
      gender: profile?.gender ?? '',
      marital_status: profile?.marital_status ?? '',
      registration_place: profile?.registration_place ?? '',
      residence_place: profile?.residence_place ?? '',
    },
  })

  const {
    fields: languageFields,
    append: appendLanguage,
    remove: removeLanguage,
  } = useFieldArray({ control, name: 'languages' })

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
      highest_degree: values.highest_degree || null,
      specialization: values.specialization || null,
      university: values.university || null,
      experience: values.experience || null,
      skills_text: values.skills_text || null,
      services_offered: values.services_offered || null,
      // Always sent, even when empty: an omitted key means "leave as-is",
      // so clearing the last language has to be an explicit empty list.
      languages: (values.languages ?? []).map((language) => ({
        name: language.name,
        proficiency: language.proficiency,
      })),
      full_name: values.full_name || null,
      birth_year: values.birth_year ? Number(values.birth_year) : null,
      gender: values.gender || null,
      marital_status: values.marital_status || null,
      registration_place: values.registration_place || null,
      residence_place: values.residence_place || null,
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

      {/* --- Published professional detail ------------------------------ */}
      <section className="space-y-5 border-t border-ink-100 pt-6">
        <div>
          <h2 className="text-lg font-bold">{t('talentForm.professionalHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('talentForm.professionalHint')}</p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label={t('talentForm.highestDegree')} error={errors.highest_degree?.message}>
            {(props) => <Input {...props} {...register('highest_degree')} />}
          </Field>
          <Field label={t('talentForm.specialization')} error={errors.specialization?.message}>
            {(props) => <Input {...props} {...register('specialization')} />}
          </Field>
        </div>

        <Field label={t('talentForm.university')} error={errors.university?.message}>
          {(props) => <Input {...props} {...register('university')} />}
        </Field>

        <Field label={t('talentForm.experience')} error={errors.experience?.message}>
          {(props) => <Textarea {...props} {...register('experience')} rows={4} />}
        </Field>

        <Field
          label={t('talentForm.skillsText')}
          hint={t('talentForm.skillsTextHint')}
          error={errors.skills_text?.message}
        >
          {(props) => <Textarea {...props} {...register('skills_text')} rows={2} />}
        </Field>

        <Field
          label={t('talentForm.servicesOffered')}
          hint={t('talentForm.servicesOfferedHint')}
          error={errors.services_offered?.message}
        >
          {(props) => <Textarea {...props} {...register('services_offered')} rows={3} />}
        </Field>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-ink-700">
              {t('talentForm.languages')}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => appendLanguage({ name: '', proficiency: 'GOOD' })}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('talentForm.addLanguage')}
            </Button>
          </div>

          {languageFields.length === 0 ? (
            <p className="text-sm text-ink-500">{t('talentForm.noLanguages')}</p>
          ) : (
            <ul className="space-y-3">
              {languageFields.map((field, index) => (
                <li key={field.id} className="flex flex-wrap items-end gap-3">
                  <div className="min-w-[10rem] flex-1">
                    <Field
                      label={t('talentForm.languageName')}
                      error={errors.languages?.[index]?.name?.message}
                    >
                      {(props) => (
                        <Input
                          {...props}
                          {...register(`languages.${index}.name` as const)}
                          invalid={Boolean(errors.languages?.[index]?.name)}
                        />
                      )}
                    </Field>
                  </div>
                  <div className="min-w-[9rem] flex-1">
                    <Field label={t('talentForm.languageLevel')}>
                      {(props) => (
                        <Controller
                          control={control}
                          name={`languages.${index}.proficiency` as const}
                          render={({ field: select }) => (
                            <Select value={select.value} onValueChange={select.onChange}>
                              <SelectTrigger id={props.id}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {LANGUAGE_PROFICIENCIES.map((level) => (
                                  <SelectItem key={level} value={level}>
                                    {t(PROFICIENCY_KEYS[level])}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        />
                      )}
                    </Field>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-clay-600"
                    onClick={() => removeLanguage(index)}
                    aria-label={t('talentForm.removeLanguage')}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* --- Verification detail: entered here, never published --------- */}
      <section className="space-y-5 border-t border-ink-100 pt-6">
        <div>
          <h2 className="text-lg font-bold">{t('talentForm.identityHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('talentForm.identityHint')}</p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label={t('talentForm.fullName')} error={errors.full_name?.message}>
            {(props) => <Input {...props} {...register('full_name')} />}
          </Field>
          <Field
            label={t('talentForm.birthYear')}
            hint={t('talentForm.birthYearHint')}
            error={errors.birth_year?.message}
          >
            {(props) => (
              <Input
                {...props}
                {...register('birth_year')}
                inputMode="numeric"
                dir="ltr"
                placeholder="1994"
                className="ltr-nums"
                invalid={Boolean(errors.birth_year)}
              />
            )}
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label={t('talentForm.gender')}>
            {(props) => (
              <Controller
                control={control}
                name="gender"
                render={({ field }) => (
                  <Select value={field.value || ''} onValueChange={field.onChange}>
                    <SelectTrigger id={props.id}>
                      <SelectValue placeholder={t('talentForm.notSpecified')} />
                    </SelectTrigger>
                    <SelectContent>
                      {GENDERS.map((value) => (
                        <SelectItem key={value} value={value}>
                          {t(GENDER_KEYS[value])}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            )}
          </Field>

          <Field label={t('talentForm.maritalStatus')}>
            {(props) => (
              <Controller
                control={control}
                name="marital_status"
                render={({ field }) => (
                  <Select value={field.value || ''} onValueChange={field.onChange}>
                    <SelectTrigger id={props.id}>
                      <SelectValue placeholder={t('talentForm.notSpecified')} />
                    </SelectTrigger>
                    <SelectContent>
                      {MARITAL_STATUSES.map((value) => (
                        <SelectItem key={value} value={value}>
                          {t(MARITAL_STATUS_KEYS[value])}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            )}
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label={t('talentForm.registrationPlace')}
            error={errors.registration_place?.message}
          >
            {(props) => <Input {...props} {...register('registration_place')} />}
          </Field>
          <Field label={t('talentForm.residencePlace')} error={errors.residence_place?.message}>
            {(props) => <Input {...props} {...register('residence_place')} />}
          </Field>
        </div>
      </section>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" size="lg" loading={pending}>
          {submitLabel}
        </Button>
        {footer}
      </div>
    </form>
  )
}
