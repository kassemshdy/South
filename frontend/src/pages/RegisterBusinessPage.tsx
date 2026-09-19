/**
 * Applying to list a business, with no account.
 *
 * The same `BasicsForm` the dashboard wizard uses, so an applicant fills
 * exactly the fields an owner would and there is no second definition of what
 * a listing is. What the wizard does afterwards — location, photos, products
 * — waits until there is an account to do it from.
 */

import { useMutation } from '@tanstack/react-query'

import { useToast } from '@/components/ui/Toast'
import { BasicsForm } from '@/features/businesses/BasicsForm'
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

  useSeo({ title: t('register.businessSeoTitle'), description: t('register.businessSubtitle') })

  const apply = useMutation({
    mutationFn: (input: {
      applicant: Applicant
      payload: BusinessPayload
      token: string | null
    }) => registrationApi.business(input.applicant, input.payload, input.token),
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
      {({ requireApplicant, captchaToken, captcha }) => (
        <BasicsForm
          submitLabel={t('register.submit')}
          identityElsewhere={false}
          pending={apply.isPending}
          serverError={unwrapFieldErrors(apply.error, 'business')}
          onSubmit={(payload) => {
            const applicant = requireApplicant()
            if (!applicant) return
            apply.mutate({ applicant, payload, token: captchaToken })
          }}
          footer={captcha}
        />
      )}
    </RegistrationShell>
  )
}
