/**
 * The switch for sign-up by SMS code, and its daily limit (the owners'
 * decision, 9 Nov 2026: on and off at will, so a problem with the SMS
 * provider sends people back to the application form). Manager-only on the
 * server; the card is hidden from other roles.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

export function SmsSignupSettings() {
  const canManage = useStaffCan('manage')
  return canManage ? <SmsSignupSettingsCard /> : null
}

function SmsSignupSettingsCard() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const saved = useQuery({
    queryKey: queryKeys.adminSmsSignup,
    queryFn: adminApi.smsSignupSettings,
  })
  const [enabled, setEnabled] = useState(false)
  const [cap, setCap] = useState('300')
  useEffect(() => {
    if (saved.data) {
      setEnabled(saved.data.enabled)
      setCap(String(saved.data.daily_cap))
    }
  }, [saved.data])

  const save = useMutation({
    mutationFn: () => adminApi.setSmsSignupSettings(enabled, Number(cap)),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.adminSmsSignup, result)
      void queryClient.invalidateQueries({ queryKey: queryKeys.phoneAuthConfig })
      toast.success(t('smsSignup.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const capNumber = Number(cap)
  const capValid = Number.isInteger(capNumber) && capNumber >= 1 && capNumber <= 5000

  return (
    <Card>
      <CardBody className="space-y-4">
        <div>
          <h2 className="text-xl font-bold">{t('smsSignup.title')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('smsSignup.intro')}</p>
        </div>
        {saved.data && !saved.data.sms_configured ? (
          <p className="rounded-xl bg-clay-50 px-3 py-2 text-sm text-clay-800">
            {t('smsSignup.notConfigured')}
          </p>
        ) : null}
        <label className="flex items-center gap-3 font-semibold text-ink-900">
          <input
            type="checkbox"
            className="h-5 w-5 accent-brand-700"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          {t('smsSignup.enabled')}
        </label>
        <Field label={t('smsSignup.dailyCap')}>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="number"
              inputMode="numeric"
              min={1}
              max={5000}
              dir="ltr"
              className="ltr-nums max-w-40"
              value={cap}
              onChange={(event) => setCap(event.target.value)}
              invalid={!capValid}
            />
          )}
        </Field>
        {saved.data ? (
          <p className="text-sm text-ink-500">
            {t('smsSignup.sentToday', { count: saved.data.sent_today })}
          </p>
        ) : null}
        <Button loading={save.isPending} disabled={!capValid} onClick={() => save.mutate()}>
          {t('smsSignup.save')}
        </Button>
      </CardBody>
    </Card>
  )
}
