/**
 * Applying to list a talent profile, with no account.
 *
 * The counterpart to `RegisterBusinessPage`, reusing the same `TalentForm`
 * the dashboard uses. The photo is not asked for here: the profile cannot
 * publish without one, but an unauthenticated file upload is not something
 * this API accepts, so it is collected after sign-in and before the profile
 * goes live.
 */

import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useToast } from '@/components/ui/Toast'
import { RegistrationShell, unwrapFieldErrors } from '@/features/onboarding/RegistrationShell'
import { kindFromQuery } from '@/features/talent/kind'
import { TalentForm } from '@/features/talent/TalentForm'
import { RegistrationLogoField } from '@/features/onboarding/RegistrationLogoField'
import { PhoneSignupGate } from '@/features/auth/PhoneSignup'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import {
  registrationApi,
  type Applicant,
  type TalentPayload,
} from '@/services/api/endpoints'

export function RegisterTalentPage() {
  const t = useT()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const initialKind = kindFromQuery(searchParams.get('kind'))
  const [logo, setLogo] = useState<File | null>(null)
  const [logoError, setLogoError] = useState<string | undefined>(undefined)

  useSeo({ title: t('register.talentSeoTitle'), description: t('register.talentSubtitle') })

  const apply = useMutation({
    mutationFn: (input: {
      applicant: Applicant
      payload: TalentPayload
      token: string | null
    }) => registrationApi.talent(input.applicant, input.payload, input.token, logo),
    onError: (error) =>
      toast.error(
        t('register.failed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  return (
    <PhoneSignupGate
      next={`/dashboard/talent${initialKind ? `?kind=${initialKind}` : ''}`}
      formRequested={searchParams.get('form') === '1'}
    >
    <RegistrationShell
      titleKey="register.talentTitle"
      subtitleKey="register.talentSubtitle"
      submitted={apply.isSuccess}
    >
      {({ requireApplicant, reportInvalid, resetCaptcha, captchaToken, captcha }) => (
        <TalentForm
          initialKind={initialKind}
          submitLabel={t('register.submit')}
          identityElsewhere={false}
          pending={apply.isPending}
          serverError={unwrapFieldErrors(apply.error, 'talent')}
          onSubmit={(payload) => {
            const applicant = requireApplicant()
            if (!applicant) return
            apply.mutate(
              { applicant, payload, token: captchaToken },
              { onError: resetCaptcha },
            )
          }}
          onInvalid={reportInvalid}
          footer={
            <>
              <RegistrationLogoField
                file={logo}
                error={logoError}
                required={false}
                label={t('register.talentPhoto')}
                onPick={(file, error) => {
                  setLogo(file)
                  setLogoError(error ?? undefined)
                }}
              />
              {captcha}
              <Link
                to="/register/business"
                className="self-center text-sm text-brand-700 hover:underline"
              >
                {t('register.switchToBusiness')}
              </Link>
            </>
          }
        />
      )}
    </RegistrationShell>
    </PhoneSignupGate>
  )
}
