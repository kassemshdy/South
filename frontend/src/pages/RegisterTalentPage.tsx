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
import { Link } from 'react-router-dom'

import { useToast } from '@/components/ui/Toast'
import { RegistrationShell, unwrapFieldErrors } from '@/features/onboarding/RegistrationShell'
import { TalentForm } from '@/features/talent/TalentForm'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { registrationApi, type TalentPayload } from '@/services/api/endpoints'

export function RegisterTalentPage() {
  const t = useT()
  const toast = useToast()

  useSeo({ title: t('register.talentSeoTitle'), description: t('register.talentSubtitle') })

  const apply = useMutation({
    mutationFn: (input: { phone: string; payload: TalentPayload; token: string | null }) =>
      registrationApi.talent(input.phone, input.payload, input.token),
    onError: (error) =>
      toast.error(
        t('register.failed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  return (
    <RegistrationShell
      titleKey="register.talentTitle"
      subtitleKey="register.talentSubtitle"
      submitted={apply.isSuccess}
    >
      {({ requireLoginPhone, captchaToken, captcha }) => (
        <TalentForm
          submitLabel={t('register.submit')}
          pending={apply.isPending}
          serverError={unwrapFieldErrors(apply.error, 'talent')}
          onSubmit={(payload) => {
            const phone = requireLoginPhone()
            if (!phone) return
            apply.mutate({ phone, payload, token: captchaToken })
          }}
          footer={
            <>
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
  )
}
