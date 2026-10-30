/**
 * Applying to list a business, with no account.
 *
 * The same `BasicsForm` the dashboard wizard uses, so an applicant fills
 * exactly the fields an owner would and there is no second definition of what
 * a listing is. The logo is asked for here too, because a shop cannot be
 * approved without one; the rest of what the wizard does afterwards — photos,
 * products — waits until there is an account to do it from.
 */

import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useToast } from '@/components/ui/Toast'
import { BasicsForm } from '@/features/businesses/BasicsForm'
import { originFromParams } from '@/features/onboarding/destinations'
import { RegistrationLogoField } from '@/features/onboarding/RegistrationLogoField'
import { RegistrationShell, unwrapFieldErrors } from '@/features/onboarding/RegistrationShell'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import {
  registrationApi,
  type Applicant,
  type BusinessPayload,
} from '@/services/api/endpoints'

export function RegisterBusinessPage() {
  const t = useT()
  const toast = useToast()
  // The goods door the visitor came through: made in the South, or imported.
  const [searchParams] = useSearchParams()
  const origin = originFromParams(searchParams)
  const [logo, setLogo] = useState<File | null>(null)
  const [logoError, setLogoError] = useState<string | undefined>(undefined)

  useSeo({ title: t('register.businessSeoTitle'), description: t('register.businessSubtitle') })

  const apply = useMutation({
    mutationFn: (input: {
      applicant: Applicant
      payload: BusinessPayload
      logo: File
      token: string | null
    }) => registrationApi.business(input.applicant, input.payload, input.logo, input.token),
    onError: (error) =>
      toast.error(
        t('register.failed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  return (
    <RegistrationShell
      titleKey="register.businessTitle"
      subtitleKey="register.businessSubtitle"
      submitted={apply.isSuccess}
    >
      {({ requireApplicant, reportInvalid, resetCaptcha, captchaToken, captcha }) => (
        <BasicsForm
          key={origin ?? 'LOCAL'}
          defaultOrigin={origin}
          submitLabel={t('register.submit')}
          identityElsewhere={false}
          askLocation
          pending={apply.isPending}
          serverError={unwrapFieldErrors(apply.error, 'business')}
          onSubmit={(payload) => {
            const applicant = requireApplicant()
            if (!logo) setLogoError(t('register.logoRequired'))
            if (!applicant || !logo) return
            apply.mutate(
              { applicant, payload, logo, token: captchaToken },
              { onError: resetCaptcha },
            )
          }}
          onInvalid={() => {
            if (!logo) setLogoError(t('register.logoRequired'))
            reportInvalid()
          }}
          footer={
            <>
              <RegistrationLogoField
                file={logo}
                error={logoError}
                onPick={(file, error) => {
                  setLogo(file)
                  setLogoError(error ?? undefined)
                }}
              />
              {captcha}
            </>
          }
        />
      )}
    </RegistrationShell>
  )
}
