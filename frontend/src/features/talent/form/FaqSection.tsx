import { Plus, Trash2 } from 'lucide-react'
import { useFieldArray, type Control, type FieldErrors, type UseFormRegister } from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { useT } from '@/i18n'
import type { TalentValues } from '@/utils/validation'

/**
 * Questions a visitor would ask, answered by the provider (the owners'
 * services redesign, 3 Nov 2026): shown on the profile as a short list a
 * visitor can open one at a time.
 */
export function FaqSection({
  control,
  register,
  errors,
}: {
  control: Control<TalentValues>
  register: UseFormRegister<TalentValues>
  errors: FieldErrors<TalentValues>
}) {
  const t = useT()
  const { fields, append, remove } = useFieldArray({ control, name: 'faqs' })

  return (
    <section className="space-y-4 rounded-2xl border border-ink-100 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{t('serviceFaqs.heading')}</h2>
          <p className="text-sm text-ink-500">{t('serviceFaqs.hint')}</p>
        </div>
        {fields.length < 15 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ question: '', answer: '' })}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('serviceFaqs.add')}
          </Button>
        ) : null}
      </div>

      <ol className="space-y-4">
        {fields.map((field, index) => {
          const entryErrors = errors.faqs?.[index]
          return (
            <li key={field.id} className="space-y-3 rounded-xl bg-sand-50 p-4">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <Field label={t('serviceFaqs.question')} required error={entryErrors?.question?.message}>
                    {(props) => (
                      <Input
                        {...props}
                        {...register(`faqs.${index}.question` as const)}
                        invalid={Boolean(entryErrors?.question)}
                        maxLength={200}
                      />
                    )}
                  </Field>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-7 text-clay-600"
                  onClick={() => remove(index)}
                  aria-label={t('serviceFaqs.remove')}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              <Field label={t('serviceFaqs.answer')} required error={entryErrors?.answer?.message}>
                {(props) => (
                  <Textarea
                    {...props}
                    {...register(`faqs.${index}.answer` as const)}
                    invalid={Boolean(entryErrors?.answer)}
                    rows={3}
                    maxLength={1000}
                  />
                )}
              </Field>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
