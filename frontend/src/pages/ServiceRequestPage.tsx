import { useMutation } from '@tanstack/react-query'
import { Check, Send, Wrench } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { LocationCombobox } from '@/components/ui/LocationCombobox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { Turnstile } from '@/components/ui/Turnstile'
import { useLocationGroups, useTalentSkills } from '@/hooks/useTaxonomy'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { openServiceRequestApi } from '@/services/api/endpoints'

const ANY = '__any__'

/**
 * "Request a service" (the owners' services redesign, 3 Nov 2026): a
 * visitor who does not want to pick a provider describes what they need, and
 * the team finds someone and puts them in touch. The trade and the town are
 * optional hints. Anonymous, like the partner form, so the server rate limits
 * it and asks for the captcha when one is configured.
 */
export function ServiceRequestPage() {
  const t = useT()
  const toast = useToast()
  const skills = useTalentSkills()
  const { groups } = useLocationGroups()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [details, setDetails] = useState('')
  const [skillId, setSkillId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)

  useSeo({
    title: `${t('openRequest.title')} | ${t('app.name')}`,
    description: t('openRequest.subtitle'),
  })

  const send = useMutation({
    mutationFn: () =>
      openServiceRequestApi.send(
        {
          customer_name: name,
          customer_phone: phone,
          details,
          skill_id: skillId || null,
          location_id: locationId || null,
        },
        captchaToken,
      ),
    onError: (error) =>
      toast.error(t('openRequest.sendFailed'), error instanceof ApiError ? error.message : undefined),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    send.mutate()
  }

  if (send.isSuccess) {
    return (
      <div className="container-page flex max-w-xl justify-center py-16">
        <Card className="w-full">
          <CardBody className="p-8 text-center">
            <Check className="mx-auto h-10 w-10 text-olive-700" aria-hidden="true" />
            <h1 className="mt-4 text-2xl">{t('openRequest.sentTitle')}</h1>
            <p className="mt-2 text-ink-500">{send.data.message}</p>
            <Button asChild variant="outline" className="mt-6">
              <Link to="/services">{t('openRequest.backToServices')}</Link>
            </Button>
          </CardBody>
        </Card>
      </div>
    )
  }

  const serviceSkills = (skills.data ?? []).filter((skill) => skill.is_active !== false)

  return (
    <div className="container-page max-w-2xl py-10">
      <header className="mb-6">
        <Wrench className="h-8 w-8 text-brand-700" aria-hidden="true" />
        <h1 className="mt-3 text-3xl">{t('openRequest.title')}</h1>
        <p className="mt-2 text-ink-500">{t('openRequest.subtitle')}</p>
      </header>

      <Card>
        <CardBody className="p-6">
          <form onSubmit={submit} className="space-y-5">
            <Field label={t('openRequest.details')} hint={t('openRequest.detailsHint')} required>
              {(props) => (
                <Textarea
                  {...props}
                  rows={5}
                  required
                  minLength={10}
                  maxLength={1000}
                  value={details}
                  onChange={(event) => setDetails(event.target.value)}
                />
              )}
            </Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t('openRequest.skill')}>
                {(props) => (
                  <Select
                    value={skillId || ANY}
                    onValueChange={(value) => setSkillId(value === ANY ? '' : value)}
                  >
                    <SelectTrigger id={props.id}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={ANY}>{t('openRequest.skillAny')}</SelectItem>
                      {serviceSkills.map((skill) => (
                        <SelectItem key={skill.id} value={skill.id}>
                          {skill.name_ar}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </Field>
              <Field label={t('openRequest.location')}>
                {(props) => (
                  <LocationCombobox
                    id={props.id}
                    value={locationId}
                    onChange={setLocationId}
                    groups={groups}
                    emptyLabel={t('openRequest.locationAny')}
                  />
                )}
              </Field>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t('openRequest.name')} required>
                {(props) => (
                  <Input
                    {...props}
                    required
                    minLength={2}
                    maxLength={80}
                    autoComplete="name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                )}
              </Field>
              <Field label={t('openRequest.phone')} required>
                {(props) => (
                  <Input
                    {...props}
                    required
                    type="tel"
                    inputMode="tel"
                    dir="ltr"
                    autoComplete="tel"
                    minLength={6}
                    maxLength={20}
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                  />
                )}
              </Field>
            </div>
            <Turnstile onToken={setCaptchaToken} />
            <Button type="submit" size="lg" loading={send.isPending}>
              <Send className="h-5 w-5" aria-hidden="true" />
              {t('openRequest.submit')}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
