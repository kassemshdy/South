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
import { useApplyServerFieldErrors } from '@/utils/serverFieldErrors'
import type { TalentPayload } from '@/services/api/endpoints'
import type { OwnerTalent } from '@/types/api'
import { talentSchema, type TalentValues } from '@/utils/validation'

import { LANGUAGE_PROFICIENCIES, PROFICIENCY_KEYS } from './labels'

interface TalentFormProps {
  profile?: OwnerTalent | undefined
  submitLabel: string
  pending?: boolean
  onSubmit: (payload: TalentPayload) => void
  /** The parent's last save failure, so a 422 lands on the right input. */
  serverError?: unknown
  footer?: React.ReactNode
}

/** The whole profile on one form — a talent profile is small enough not to
 * need the multi-step wizard a business listing gets. */
export function TalentForm({ profile, submitLabel, pending, onSubmit, serverError, footer }: TalentFormProps) {
  const skills = useTalentSkills()
  const { groups } = useLocationGroups()
  const t = useT()
  const otherSkillId = skills.data?.find((skill) => skill.slug === 'other')?.id
  const schema = useMemo(() => talentSchema(t, otherSkillId), [t, otherSkillId])

  const {
    register,
    handleSubmit,
    control,
    setError,
    getValues,
    formState: { errors },
  } = useForm<TalentValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: profile?.display_name ?? '',
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
      // Stored as an id; shown as the link the person originally pasted.
      video_url: profile?.youtube_video_id
        ? `https://www.youtube.com/watch?v=${profile.youtube_video_id}`
        : '',
      highest_degree: profile?.highest_degree ?? '',
      specialization: profile?.specialization ?? '',
      university: profile?.university ?? '',
      education_years:
        profile?.education_years !== null && profile?.education_years !== undefined
          ? String(profile.education_years)
          : '',
      graduation_date: profile?.graduation_date ?? '',
      study_focus: profile?.study_focus ?? '',
      experience: profile?.experience ?? '',
      professional_training: profile?.professional_training ?? '',
      skills_text: profile?.skills_text ?? '',
      services_offered: profile?.services_offered ?? '',
      hobbies: profile?.hobbies ?? '',
      employment_type: profile?.employment_type ?? '',
      remote_capable: profile?.remote_capable ?? false,
      languages:
        profile?.languages?.map((language) => ({
          name: language.name,
          proficiency: language.proficiency,
        })) ?? [],
    },
  })

  const {
    fields: languageFields,
    append: appendLanguage,
    remove: removeLanguage,
  } = useFieldArray({ control, name: 'languages' })

  const skillId = useWatch({ control, name: 'skill_id' })
  const isOtherSkill = Boolean(otherSkillId) && skillId === otherSkillId

  useApplyServerFieldErrors(serverError, setError, getValues)

  const submit = handleSubmit((values) => {
    onSubmit({
      display_name: values.display_name,
      bio: values.bio || null,
      years_experience: values.years_experience ? Number(values.years_experience) : null,
      skill_id: values.skill_id || null,
      custom_skill_text: values.custom_skill_text || null,
      location_id: values.location_id || null,
      phone: values.phone || null,
      whatsapp: values.whatsapp || null,
      email: values.email || null,
      website: values.website || null,
      video_url: values.video_url || null,
      highest_degree: values.highest_degree || null,
      specialization: values.specialization || null,
      university: values.university || null,
      education_years: values.education_years ? Number(values.education_years) : null,
      graduation_date: values.graduation_date || null,
      study_focus: values.study_focus || null,
      experience: values.experience || null,
      professional_training: values.professional_training || null,
      skills_text: values.skills_text || null,
      services_offered: values.services_offered || null,
      hobbies: values.hobbies || null,
      employment_type: (values.employment_type || null) as TalentPayload['employment_type'],
      remote_capable: values.remote_capable,
      // Always sent, even when empty: an omitted key means "leave as-is",
      // so clearing the last language has to be an explicit empty list.
      languages: (values.languages ?? []).map((language) => ({
        name: language.name,
        proficiency: language.proficiency,
      })),
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

        {/* Spans both columns: the hint explaining what the video is for
            needs the width, and a half-width field beside a phone number
            reads as another contact detail rather than a page section. */}
        <div className="sm:col-span-2">
          <Field
            label={t('form.videoUrl')}
            hint={t('form.videoUrlHint')}
            error={errors.video_url?.message}
          >
            {(props) => (
              <Input
                {...props}
                {...register('video_url')}
                type="url"
                dir="ltr"
                className="ltr-nums"
                placeholder="youtube.com/watch?v=..."
                invalid={Boolean(errors.video_url)}
              />
            )}
          </Field>
        </div>
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

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label={t('talentForm.educationYears')} error={errors.education_years?.message}>
            {(props) => (
              <Input
                {...props}
                {...register('education_years')}
                inputMode="numeric"
                dir="ltr"
                className="ltr-nums"
                invalid={Boolean(errors.education_years)}
              />
            )}
          </Field>
          <Field label={t('talentForm.graduationDate')} error={errors.graduation_date?.message}>
            {(props) => (
              <Input
                {...props}
                {...register('graduation_date')}
                type="date"
                dir="ltr"
                className="ltr-nums"
                invalid={Boolean(errors.graduation_date)}
              />
            )}
          </Field>
        </div>

        <Field
          label={t('talentForm.studyFocus')}
          hint={t('talentForm.studyFocusHint')}
          error={errors.study_focus?.message}
        >
          {(props) => <Textarea {...props} {...register('study_focus')} rows={2} />}
        </Field>

        <Field label={t('talentForm.experience')} error={errors.experience?.message}>
          {(props) => <Textarea {...props} {...register('experience')} rows={4} />}
        </Field>

        <Field
          label={t('talentForm.professionalTraining')}
          hint={t('talentForm.professionalTrainingHint')}
          error={errors.professional_training?.message}
        >
          {(props) => <Textarea {...props} {...register('professional_training')} rows={2} />}
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

        <Field
          label={t('talentForm.hobbies')}
          hint={t('talentForm.hobbiesHint')}
          error={errors.hobbies?.message}
        >
          {(props) => <Textarea {...props} {...register('hobbies')} rows={2} />}
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label={t('talentForm.employmentType')} error={errors.employment_type?.message}>
            {(props) => (
              <Controller
                control={control}
                name="employment_type"
                render={({ field }) => (
                  <Select value={field.value ?? ''} onValueChange={field.onChange}>
                    <SelectTrigger id={props.id}>
                      <SelectValue placeholder={t('talentForm.employmentTypePlaceholder')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="FULL_TIME">{t('talentForm.employmentTypeFullTime')}</SelectItem>
                      <SelectItem value="PART_TIME">{t('talentForm.employmentTypePartTime')}</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            )}
          </Field>

          <label className="flex items-center gap-3 self-end rounded-xl border-2 border-ink-100 p-3.5">
            <input type="checkbox" {...register('remote_capable')} className="h-5 w-5 accent-brand-600" />
            <span className="font-medium">{t('talentForm.remoteCapable')}</span>
          </label>
        </div>

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

      {/* Identity is set on the account, not here: one legal name per
          person, however many listings they own. */}
      <p className="rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
        {t('talentForm.identityMovedNote')}
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
