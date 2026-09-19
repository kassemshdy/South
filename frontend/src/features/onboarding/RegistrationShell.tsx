/**
 * The frame both public application forms sit in.
 *
 * Applying is not signing up. Nothing here creates a session, and nothing an
 * applicant fills in goes live: the listing is stored pending review, and an
 * administrator decides. So the page has to say that plainly before the first
 * input, and say it again at the end — someone who fills a long form and then
 * cannot find their shop on the site has been misled by the form.
 *
 * What this adds around the listing form it wraps is the three things an
 * applicant has and an owner does not: the phone number that will become
 * their login, who they are, and the captcha. All three live here rather than
 * inside `BasicsForm` / `TalentForm`, which are also used from the dashboard
 * by people who already have an account carrying the first two.
 *
 * The identity block is the same one the account page edits, asked here
 * because the reviewer is deciding whether this is a real person from the
 * South — collecting it after the audit would put the decision before the
 * evidence. It is written onto the account, not the listing, and no public
 * payload carries it: the reviewer reads it back on the screen they are
 * already looking at.
 */

import { CheckCircle2, MessageCircle, Phone, ShieldCheck, UserRound } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Turnstile } from '@/components/ui/Turnstile'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import type { Applicant, ApplicantIdentity } from '@/services/api/endpoints'
import { isLebanesePhone } from '@/utils/validation'

/**
 * Moves a 422's per-field sentences from `business.name` onto `name`.
 *
 * The registration payload nests the listing under one key, so the API names
 * the field the way it received it; the form inside knows its fields by their
 * bare names. Without this the sentence has no input to land on and is
 * silently dropped — which is the bug `serverFieldErrors` exists to fix, so
 * re-introducing it one level up would be a poor trade.
 */
export function unwrapFieldErrors(error: unknown, prefix: string): unknown {
  if (!(error instanceof ApiError)) return error
  return new ApiError(
    error.status,
    {
      error: {
        code: error.code,
        message: error.message,
        details: {
          fields: error.fields.map(({ field, message }) => ({
            field: field.startsWith(`${prefix}.`) ? field.slice(prefix.length + 1) : field,
            message,
          })),
        },
      },
    },
    error.message,
  )
}

type IdentityField = keyof ApplicantIdentity

const IDENTITY_FIELDS: IdentityField[] = [
  'full_name',
  'birth_year',
  'registration_place',
  'residence_place',
]

const IDENTITY_LABELS: Record<IdentityField, TranslationKey> = {
  full_name: 'account.fullNameLabel',
  birth_year: 'account.birthYearLabel',
  registration_place: 'account.registrationPlaceLabel',
  residence_place: 'account.residencePlaceLabel',
}

const IDENTITY_MISSING: Record<IdentityField, TranslationKey> = {
  full_name: 'validation.fullNameRequired',
  birth_year: 'validation.birthYearInvalid',
  registration_place: 'validation.registrationPlaceRequired',
  residence_place: 'validation.residencePlaceRequired',
}

interface RegistrationShellProps {
  titleKey: TranslationKey
  subtitleKey: TranslationKey
  /** Rendered with the captcha token this frame collects. */
  children: (frame: {
    loginPhone: string
    captchaToken: string | null
    /**
     * Everything this frame collects, or null with the errors on screen.
     *
     * One call rather than one per block, so a caller cannot validate the
     * phone number, forget the identity, and send an application the API
     * then refuses for a field the form never marked.
     */
    requireApplicant: () => Applicant | null
    captcha: ReactNode
  }) => ReactNode
  /** Shown instead of the form once the application has been accepted. */
  submitted: boolean
}

export function RegistrationShell({
  titleKey,
  subtitleKey,
  children,
  submitted,
}: RegistrationShellProps) {
  const t = useT()
  const [loginPhone, setLoginPhone] = useState('')
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const [identity, setIdentity] = useState<Record<IdentityField, string>>({
    full_name: '',
    birth_year: '',
    registration_place: '',
    residence_place: '',
  })
  const [identityErrors, setIdentityErrors] = useState<
    Partial<Record<IdentityField, string>>
  >({})

  const requirePhone = (): string | null => {
    const value = loginPhone.trim()
    if (!value) {
      setPhoneError(t('validation.phoneRequired'))
      return null
    }
    if (!isLebanesePhone(value)) {
      setPhoneError(t('validation.phoneInvalid'))
      return null
    }
    setPhoneError(null)
    return value
  }

  const requireIdentity = (): ApplicantIdentity | null => {
    const errors: Partial<Record<IdentityField, string>> = {}
    for (const field of IDENTITY_FIELDS) {
      if (!identity[field].trim()) errors[field] = t(IDENTITY_MISSING[field])
    }
    // A year rather than an age: an age entered once is wrong a year later,
    // and anything that needs one can work it out.
    const year = Number(identity.birth_year.trim())
    if (!errors.birth_year && (!Number.isInteger(year) || year < 1900 || year > 2100)) {
      errors.birth_year = t('validation.birthYearInvalid')
    }

    setIdentityErrors(errors)
    if (Object.keys(errors).length > 0) return null

    return {
      full_name: identity.full_name.trim(),
      birth_year: year,
      registration_place: identity.registration_place.trim(),
      residence_place: identity.residence_place.trim(),
    }
  }

  const requireApplicant = (): Applicant | null => {
    // Both, always, rather than stopping at the first failure: somebody who
    // has left two fields blank should be told about two fields.
    const phone = requirePhone()
    const values = requireIdentity()
    if (!phone || !values) return null
    return { phone, identity: values }
  }

  if (submitted) return <SubmittedPanel phone={loginPhone} />

  return (
    <div className="container-page max-w-3xl py-10">
      <header className="mb-6">
        <h1 className="text-3xl">{t(titleKey)}</h1>
        <p className="mt-2 text-ink-500">{t(subtitleKey)}</p>
      </header>

      <HowItWorks />

      <Card className="mb-6">
        <CardBody className="space-y-4 p-6">
          <div className="flex items-center gap-2 text-ink-900">
            <Phone className="h-5 w-5 text-brand-700" aria-hidden="true" />
            <h2 className="text-lg">{t('register.loginPhoneHeading')}</h2>
          </div>
          <Field
            label={t('register.loginPhoneLabel')}
            required
            error={phoneError ?? undefined}
            hint={t('register.loginPhoneHint')}
          >
            {(props) => (
              <Input
                {...props}
                value={loginPhone}
                onChange={(event) => {
                  setLoginPhone(event.target.value)
                  if (phoneError) setPhoneError(null)
                }}
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                dir="ltr"
                placeholder="03 123 456"
                className="ltr-nums"
                invalid={Boolean(phoneError)}
              />
            )}
          </Field>
        </CardBody>
      </Card>

      <Card className="mb-6">
        <CardBody className="space-y-4 p-6">
          <div className="flex items-center gap-2 text-ink-900">
            <UserRound className="h-5 w-5 text-brand-700" aria-hidden="true" />
            <h2 className="text-lg">{t('register.identityHeading')}</h2>
          </div>
          <p className="text-sm text-ink-500">{t('register.identityHint')}</p>

          <div className="grid gap-5 sm:grid-cols-2">
            {IDENTITY_FIELDS.map((field) => (
              <Field
                key={field}
                label={t(IDENTITY_LABELS[field])}
                required
                error={identityErrors[field]}
                hint={field === 'birth_year' ? t('account.birthYearHint') : undefined}
              >
                {(props) => (
                  <Input
                    {...props}
                    value={identity[field]}
                    onChange={(event) => {
                      const value = event.target.value
                      setIdentity((current) => ({ ...current, [field]: value }))
                      if (identityErrors[field]) {
                        setIdentityErrors((current) => ({ ...current, [field]: undefined }))
                      }
                    }}
                    {...(field === 'birth_year'
                      ? {
                          inputMode: 'numeric' as const,
                          dir: 'ltr' as const,
                          placeholder: '1994',
                          className: 'ltr-nums',
                        }
                      : {})}
                    invalid={Boolean(identityErrors[field])}
                  />
                )}
              </Field>
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="p-6">
          {children({
            loginPhone,
            captchaToken,
            requireApplicant,
            captcha: <Turnstile onToken={setCaptchaToken} />,
          })}
        </CardBody>
      </Card>

      <p className="mt-6 text-center text-sm text-ink-500">
        {t('register.alreadyHaveAccount')}{' '}
        <Link to="/login" className="text-brand-700 hover:underline">
          {t('register.signInLink')}
        </Link>
      </p>
    </div>
  )
}

/** Three sentences, because the sequence is not the one people expect. */
function HowItWorks() {
  const t = useT()
  const steps: { icon: typeof Phone; key: TranslationKey }[] = [
    { icon: Phone, key: 'register.stepApply' },
    { icon: ShieldCheck, key: 'register.stepReview' },
    { icon: MessageCircle, key: 'register.stepCredentials' },
  ]

  return (
    <ol className="mb-6 grid gap-3 sm:grid-cols-3">
      {steps.map(({ icon: Icon, key }, index) => (
        <li key={key} className="flex gap-3 rounded-2xl bg-sand-100 p-4 text-sm text-clay-800">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-brand-700">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          <span>
            <span className="ltr-nums block font-semibold text-ink-900">{index + 1}</span>
            {t(key)}
          </span>
        </li>
      ))}
    </ol>
  )
}

function SubmittedPanel({ phone }: { phone: string }) {
  const t = useT()
  return (
    <div className="container-page flex max-w-xl justify-center py-16">
      <Card className="w-full">
        <CardBody className="p-8 text-center">
          <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
            <CheckCircle2 className="h-7 w-7" aria-hidden="true" />
          </span>
          <h1 className="text-2xl">{t('register.doneTitle')}</h1>
          <p className="mt-3 text-ink-500">{t('register.doneBody')}</p>
          {phone ? (
            <p className="mt-2 text-ink-500">
              {t('register.doneOnNumber')}{' '}
              <span className="ltr-nums font-semibold text-ink-900">{phone}</span>
            </p>
          ) : null}
          <Link
            to="/"
            className="mt-6 inline-block rounded-xl bg-brand-700 px-5 py-2.5 text-white hover:bg-brand-800"
          >
            {t('register.doneHome')}
          </Link>
        </CardBody>
      </Card>
    </div>
  )
}
