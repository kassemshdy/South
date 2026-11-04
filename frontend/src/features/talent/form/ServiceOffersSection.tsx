import { Plus, Trash2 } from 'lucide-react'
import {
  Controller,
  useFieldArray,
  type Control,
  type FieldErrors,
  type UseFormRegister,
} from 'react-hook-form'

import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useT } from '@/i18n'
import type { TalentValues } from '@/utils/validation'

/** "20.00" as the owner typed it: "20". */
export function plainPrice(value: string | null): string {
  if (!value) return ''
  return value.replace(/\.00$/, '')
}

/**
 * A service provider's services, each with its own price (the owners'
 * services redesign, 3 Nov 2026). A price is optional; "to" makes it a
 * range. The free-text "services offered" field stays below for anything
 * that is not a priced line.
 */
export function ServiceOffersSection({
  control,
  register,
  errors,
}: {
  control: Control<TalentValues>
  register: UseFormRegister<TalentValues>
  errors: FieldErrors<TalentValues>
}) {
  const t = useT()
  const { fields, append, remove } = useFieldArray({ control, name: 'service_offers' })

  return (
    <section className="space-y-4 rounded-2xl border border-ink-100 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{t('serviceOffers.heading')}</h2>
          <p className="text-sm text-ink-500">{t('serviceOffers.hint')}</p>
        </div>
        {fields.length < 20 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              append({
                title: '',
                description: '',
                price_from: '',
                price_to: '',
                currency: 'USD',
                price_unit: '',
              })
            }
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('serviceOffers.add')}
          </Button>
        ) : null}
      </div>

      <ol className="space-y-4">
        {fields.map((field, index) => {
          const entryErrors = errors.service_offers?.[index]
          return (
            <li key={field.id} className="space-y-3 rounded-xl bg-sand-50 p-4">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <Field label={t('serviceOffers.title')} required error={entryErrors?.title?.message}>
                    {(props) => (
                      <Input
                        {...props}
                        {...register(`service_offers.${index}.title` as const)}
                        invalid={Boolean(entryErrors?.title)}
                        maxLength={120}
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
                  aria-label={t('serviceOffers.remove')}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              <div className="grid gap-3 sm:grid-cols-4">
                <Field label={t('serviceOffers.priceFrom')} error={entryErrors?.price_from?.message}>
                  {(props) => (
                    <Input
                      {...props}
                      {...register(`service_offers.${index}.price_from` as const)}
                      inputMode="decimal"
                      dir="ltr"
                      className="ltr-nums"
                      invalid={Boolean(entryErrors?.price_from)}
                    />
                  )}
                </Field>
                <Field label={t('serviceOffers.priceTo')} error={entryErrors?.price_to?.message}>
                  {(props) => (
                    <Input
                      {...props}
                      {...register(`service_offers.${index}.price_to` as const)}
                      inputMode="decimal"
                      dir="ltr"
                      className="ltr-nums"
                      invalid={Boolean(entryErrors?.price_to)}
                    />
                  )}
                </Field>
                <Field label={t('serviceOffers.currency')}>
                  {(props) => (
                    <Controller
                      control={control}
                      name={`service_offers.${index}.currency` as const}
                      render={({ field: currency }) => (
                        <Select value={currency.value} onValueChange={currency.onChange}>
                          <SelectTrigger id={props.id}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="USD">{t('serviceOffers.usd')}</SelectItem>
                            <SelectItem value="LBP">{t('serviceOffers.lbp')}</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    />
                  )}
                </Field>
                <Field label={t('serviceOffers.unit')} hint={t('serviceOffers.unitHint')}>
                  {(props) => (
                    <Input
                      {...props}
                      {...register(`service_offers.${index}.price_unit` as const)}
                      maxLength={40}
                    />
                  )}
                </Field>
              </div>
              <Field label={t('serviceOffers.description')} error={entryErrors?.description?.message}>
                {(props) => (
                  <Input
                    {...props}
                    {...register(`service_offers.${index}.description` as const)}
                    maxLength={500}
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
