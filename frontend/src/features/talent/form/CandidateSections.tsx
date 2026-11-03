import { Plus, Trash2, X } from 'lucide-react'
import { useEffect } from 'react'
import {
  Controller,
  useFieldArray,
  useWatch,
  type Control,
  type FieldErrors,
  type UseFormRegister,
  type UseFormSetValue,
} from 'react-hook-form'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useLocationGroups } from '@/hooks/useTaxonomy'
import { useT } from '@/i18n'
import type { EducationLevel, TalentAvailability, TalentWorkType } from '@/types/api'
import type { TalentValues } from '@/utils/validation'

/**
 * The job seeker's own sections of the profile form (the owners' candidate
 * directory ticket, 31 Oct 2026): what they are looking for, a dated work
 * history, education and courses, the CV and their privacy choices. Shown
 * only for a job application; a service keeps the form it had.
 */

export const WORK_TYPES: TalentWorkType[] = ['FULL_TIME', 'PART_TIME', 'REMOTE', 'TRAINING']
export const AVAILABILITIES: TalentAvailability[] = ['NOW', 'WITHIN_MONTH', 'EMPLOYED_OPEN']
export const EDUCATION_LEVELS: EducationLevel[] = [
  'SECONDARY_VOCATIONAL',
  'UNIVERSITY',
  'POSTGRADUATE',
]

interface SectionProps {
  control: Control<TalentValues>
  register: UseFormRegister<TalentValues>
  errors: FieldErrors<TalentValues>
}

const CHOICE =
  'flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border-2 border-ink-100 bg-white px-4 font-semibold text-ink-700 transition-colors hover:border-ink-300 has-[:checked]:border-brand-600 has-[:checked]:bg-brand-50 has-[:checked]:text-brand-800'

function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-bold">{children}</h2>
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick}>
      <Plus className="h-4 w-4" aria-hidden="true" />
      {label}
    </Button>
  )
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="text-clay-600"
      onClick={onClick}
      aria-label={label}
    >
      <Trash2 className="h-4 w-4" aria-hidden="true" />
    </Button>
  )
}

/** What they are looking for: the job, kinds of work, where, when, education. */
export function CandidateLookingFor({ control, register, errors }: SectionProps) {
  const t = useT()
  const { groups, byId } = useLocationGroups()

  return (
    <section className="space-y-5 border-t border-ink-100 pt-6">
      <SectionHeading>{t('candidateForm.lookingHeading')}</SectionHeading>

      <Field label={t('candidateForm.desiredTitle')} error={errors.desired_title?.message}>
        {(props) => (
          <Input
            {...props}
            {...register('desired_title')}
            maxLength={60}
            placeholder={t('candidateForm.desiredTitlePlaceholder')}
            invalid={Boolean(errors.desired_title)}
          />
        )}
      </Field>

      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-ink-700">
          {t('candidateForm.workTypes')}
        </legend>
        <Controller
          control={control}
          name="work_types"
          render={({ field }) => (
            <div className="grid gap-3 sm:grid-cols-4">
              {WORK_TYPES.map((type) => (
                <label key={type} className={CHOICE}>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-brand-700"
                    checked={field.value.includes(type)}
                    onChange={(event) =>
                      field.onChange(
                        event.target.checked
                          ? [...field.value, type]
                          : field.value.filter((value) => value !== type),
                      )
                    }
                  />
                  {t(`candidateForm.workType.${type}`)}
                </label>
              ))}
            </div>
          )}
        />
      </fieldset>

      <Controller
        control={control}
        name="work_area_ids"
        render={({ field }) => (
          <Field label={t('candidateForm.workAreas')}>
            {(props) => (
              <div className="space-y-2">
                {field.value.length > 0 ? (
                  <ul className="flex flex-wrap gap-2">
                    {field.value.map((id) => {
                      const name = byId.get(id)?.name_ar ?? id
                      return (
                        <li
                          key={id}
                          className="flex items-center gap-1 rounded-full bg-brand-50 py-1 pe-1.5 ps-3 text-sm font-semibold text-brand-800"
                        >
                          <bdi>{name}</bdi>
                          <button
                            type="button"
                            className="rounded-full p-0.5 hover:bg-brand-100"
                            aria-label={t('candidateForm.removeArea', { name })}
                            onClick={() => field.onChange(field.value.filter((v) => v !== id))}
                          >
                            <X className="h-3.5 w-3.5" aria-hidden="true" />
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                ) : null}
                <LocationCombobox
                  id={props.id}
                  aria-describedby={props['aria-describedby']}
                  value=""
                  onChange={(id: string) => {
                    if (id && !field.value.includes(id)) field.onChange([...field.value, id])
                  }}
                  groups={groups}
                  placeholder={t('candidateForm.workAreasPlaceholder')}
                />
              </div>
            )}
          </Field>
        )}
      />

      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-ink-700">
          {t('candidateForm.availability')}
        </legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {AVAILABILITIES.map((value) => (
            <label key={value} className={CHOICE}>
              <input
                type="radio"
                value={value}
                {...register('availability')}
                className="accent-brand-700"
              />
              {t(`candidateForm.availability.${value}`)}
            </label>
          ))}
        </div>
      </fieldset>

      <Field label={t('candidateForm.educationLevel')} error={errors.education_level?.message}>
        {(props) => (
          <Controller
            control={control}
            name="education_level"
            render={({ field }) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id={props.id} aria-describedby={props['aria-describedby']}>
                  <SelectValue placeholder={t('candidateForm.educationLevelPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {EDUCATION_LEVELS.map((level) => (
                    <SelectItem key={level} value={level}>
                      {t(`candidateForm.educationLevel.${level}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        )}
      </Field>
    </section>
  )
}

/** Work history: dated entries, or "no experience yet". */
export function CandidateExperience({
  control,
  register,
  errors,
  setValue,
}: SectionProps & { setValue: UseFormSetValue<TalentValues> }) {
  const t = useT()
  const { fields, append, remove } = useFieldArray({ control, name: 'experiences' })
  const noExperience = useWatch({ control, name: 'no_experience' })
  const entries = useWatch({ control, name: 'experiences' })

  useEffect(() => {
    if (noExperience && fields.length > 0) setValue('experiences', [])
  }, [noExperience, fields.length, setValue])

  return (
    <section className="space-y-4 border-t border-ink-100 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading>{t('candidateForm.experienceHeading')}</SectionHeading>
        {!noExperience ? (
          <AddButton
            label={t('candidateForm.addExperience')}
            onClick={() =>
              append({
                title: '',
                employer: '',
                town: '',
                start_date: '',
                end_date: '',
                is_current: false,
                description: '',
              })
            }
          />
        ) : null}
      </div>

      <label className="flex items-center gap-3">
        <input type="checkbox" {...register('no_experience')} className="h-5 w-5 accent-brand-600" />
        <span className="font-medium">{t('candidateForm.noExperience')}</span>
      </label>

      {!noExperience ? (
        <ol className="space-y-4">
          {fields.map((field, index) => {
            const entryErrors = errors.experiences?.[index]
            const current = entries?.[index]?.is_current ?? false
            return (
              <li key={field.id} className="space-y-3 rounded-2xl border border-ink-100 p-4">
                <div className="flex items-start gap-3">
                  <div className="grid flex-1 gap-3 sm:grid-cols-3">
                    <Field
                      label={t('candidateForm.expTitle')}
                      required
                      error={entryErrors?.title?.message}
                    >
                      {(props) => (
                        <Input
                          {...props}
                          {...register(`experiences.${index}.title` as const)}
                          invalid={Boolean(entryErrors?.title)}
                        />
                      )}
                    </Field>
                    <Field label={t('candidateForm.expEmployer')}>
                      {(props) => (
                        <Input {...props} {...register(`experiences.${index}.employer` as const)} />
                      )}
                    </Field>
                    <Field label={t('candidateForm.expTown')}>
                      {(props) => (
                        <Input {...props} {...register(`experiences.${index}.town` as const)} />
                      )}
                    </Field>
                  </div>
                  <RemoveButton label={t('candidateForm.removeEntry')} onClick={() => remove(index)} />
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <Field label={t('candidateForm.expFrom')}>
                    {(props) => (
                      <Input
                        {...props}
                        {...register(`experiences.${index}.start_date` as const)}
                        type="month"
                        dir="ltr"
                        className="ltr-nums"
                      />
                    )}
                  </Field>
                  {!current ? (
                    <Field label={t('candidateForm.expTo')}>
                      {(props) => (
                        <Input
                          {...props}
                          {...register(`experiences.${index}.end_date` as const)}
                          type="month"
                          dir="ltr"
                          className="ltr-nums"
                        />
                      )}
                    </Field>
                  ) : null}
                  <label className="flex items-center gap-3 self-end pb-3">
                    <input
                      type="checkbox"
                      {...register(`experiences.${index}.is_current` as const)}
                      className="h-5 w-5 accent-brand-600"
                    />
                    <span className="font-medium">{t('candidateForm.expCurrent')}</span>
                  </label>
                </div>
                <Field
                  label={t('candidateForm.expDescription')}
                  error={entryErrors?.description?.message}
                >
                  {(props) => (
                    <Textarea
                      {...props}
                      {...register(`experiences.${index}.description` as const)}
                      rows={3}
                      maxLength={600}
                    />
                  )}
                </Field>
              </li>
            )
          })}
        </ol>
      ) : null}
    </section>
  )
}

/** Education: degrees, then courses and certificates. */
export function CandidateEducation({ control, register, errors }: SectionProps) {
  const t = useT()
  const education = useFieldArray({ control, name: 'education' })
  const courses = useFieldArray({ control, name: 'courses' })

  return (
    <section className="space-y-4 border-t border-ink-100 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeading>{t('candidateForm.educationHeading')}</SectionHeading>
        <AddButton
          label={t('candidateForm.addEducation')}
          onClick={() =>
            education.append({ degree: '', field: '', institution: '', graduation_year: '' })
          }
        />
      </div>
      <ul className="space-y-3">
        {education.fields.map((field, index) => (
          <li key={field.id} className="flex items-start gap-3 rounded-2xl border border-ink-100 p-4">
            <div className="grid flex-1 gap-3 sm:grid-cols-4">
              <Field label={t('candidateForm.eduDegree')}>
                {(props) => <Input {...props} {...register(`education.${index}.degree` as const)} />}
              </Field>
              <Field label={t('candidateForm.eduField')}>
                {(props) => <Input {...props} {...register(`education.${index}.field` as const)} />}
              </Field>
              <Field label={t('candidateForm.eduInstitution')}>
                {(props) => (
                  <Input {...props} {...register(`education.${index}.institution` as const)} />
                )}
              </Field>
              <Field
                label={t('candidateForm.eduYear')}
                error={errors.education?.[index]?.graduation_year?.message}
              >
                {(props) => (
                  <Input
                    {...props}
                    {...register(`education.${index}.graduation_year` as const)}
                    inputMode="numeric"
                    dir="ltr"
                    className="ltr-nums"
                    invalid={Boolean(errors.education?.[index]?.graduation_year)}
                  />
                )}
              </Field>
            </div>
            <RemoveButton
              label={t('candidateForm.removeEntry')}
              onClick={() => education.remove(index)}
            />
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <h3 className="font-bold">{t('candidateForm.coursesHeading')}</h3>
        <AddButton
          label={t('candidateForm.addCourse')}
          onClick={() => courses.append({ name: '', issuer: '', year: '' })}
        />
      </div>
      <ul className="space-y-3">
        {courses.fields.map((field, index) => {
          const entryErrors = errors.courses?.[index]
          return (
            <li
              key={field.id}
              className="flex items-start gap-3 rounded-2xl border border-ink-100 p-4"
            >
              <div className="grid flex-1 gap-3 sm:grid-cols-3">
                <Field
                  label={t('candidateForm.courseName')}
                  required
                  error={entryErrors?.name?.message}
                >
                  {(props) => (
                    <Input
                      {...props}
                      {...register(`courses.${index}.name` as const)}
                      invalid={Boolean(entryErrors?.name)}
                    />
                  )}
                </Field>
                <Field label={t('candidateForm.courseIssuer')}>
                  {(props) => <Input {...props} {...register(`courses.${index}.issuer` as const)} />}
                </Field>
                <Field label={t('candidateForm.courseYear')} error={entryErrors?.year?.message}>
                  {(props) => (
                    <Input
                      {...props}
                      {...register(`courses.${index}.year` as const)}
                      inputMode="numeric"
                      dir="ltr"
                      className="ltr-nums"
                      invalid={Boolean(entryErrors?.year)}
                    />
                  )}
                </Field>
              </div>
              <RemoveButton
                label={t('candidateForm.removeEntry')}
                onClick={() => courses.remove(index)}
              />
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/**
 * Shown or not to employers, in place of the services' checkbox. A required
 * choice with nothing preselected for a new candidate: each decides.
 */
export function CandidatePhoneChoice({ register, errors }: Omit<SectionProps, 'control'>) {
  const t = useT()
  return (
    <fieldset aria-describedby={errors.phone_choice ? 'candidate-phone-choice-error' : undefined}>
      <legend className="mb-2 text-sm font-semibold text-ink-700">
        {t('candidateForm.phoneChoiceLabel')}
        <span className="ms-1 text-clay-600" aria-hidden="true">
          *
        </span>
      </legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={CHOICE}>
          <input type="radio" value="public" {...register('phone_choice')} className="accent-brand-700" />
          {t('candidateForm.phoneChoicePublic')}
        </label>
        <label className={CHOICE}>
          <input type="radio" value="private" {...register('phone_choice')} className="accent-brand-700" />
          {t('candidateForm.phoneChoicePrivate')}
        </label>
      </div>
      <p className="mt-1.5 text-sm text-ink-500">{t('candidateForm.phoneChoiceHint')}</p>
      {errors.phone_choice ? (
        <p id="candidate-phone-choice-error" role="alert" className="mt-1.5 text-sm text-clay-600">
          {errors.phone_choice.message}
        </p>
      ) : null}
    </fieldset>
  )
}

/** The CV, then contact and privacy: the photo and the note to the team. */
export function CandidatePrivacy({
  register,
  errors,
  cvOnAccountPage,
}: Omit<SectionProps, 'control'> & {
  /** The CV is uploaded on the account page; off on the public application. */
  cvOnAccountPage: boolean
}) {
  const t = useT()
  return (
    <section className="space-y-4 border-t border-ink-100 pt-6">
      <SectionHeading>{t('candidateForm.cvHeading')}</SectionHeading>
      {cvOnAccountPage ? (
        <p className="text-sm text-ink-500">
          {t('candidateForm.cvHint')}{' '}
          <Link to="/dashboard/account" className="font-semibold text-brand-700 underline">
            {t('candidateForm.cvLink')}
          </Link>
        </p>
      ) : null}
      <label className="flex items-center gap-3 rounded-xl border-2 border-ink-100 p-3.5">
        <input type="checkbox" {...register('cv_public')} className="h-5 w-5 accent-brand-600" />
        <span className="font-medium">{t('candidateForm.cvPublic')}</span>
      </label>

      <SectionHeading>{t('candidateForm.privacyHeading')}</SectionHeading>
      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-ink-100 bg-sand-50/60 p-3">
        <input type="checkbox" {...register('photo_hidden')} className="mt-1 h-4 w-4 accent-brand-700" />
        <span>
          <span className="font-semibold text-ink-900">{t('candidateForm.photoHidden')}</span>
          <span className="mt-0.5 block text-sm text-ink-500">
            {t('candidateForm.photoHiddenHint')}
          </span>
        </span>
      </label>

      <Field
        label={t('candidateForm.teamMessage')}
        hint={t('candidateForm.teamMessageHint')}
        error={errors.team_message?.message}
      >
        {(props) => (
          <Textarea
            {...props}
            {...register('team_message')}
            rows={3}
            maxLength={2000}
            invalid={Boolean(errors.team_message)}
          />
        )}
      </Field>
    </section>
  )
}
