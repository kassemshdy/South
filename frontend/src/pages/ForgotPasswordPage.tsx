/**
 * A forgotten password, without a "forgot password" email or SMS.
 *
 * There is no gateway, so the site cannot reset anything by itself. What it
 * can do is write the request: the owner types the phone number their account
 * is keyed by, and the button opens WhatsApp with a message to the team that
 * already says what happened and which account it is. An administrator then
 * issues a new password from the account's admin page and sends it back the
 * same way.
 *
 * The number it is sent to comes from `useSupportWhatsapp`. With none there is
 * nobody to send it to, so the page goes back to sign-in, and the login page
 * does not link here.
 */

import { KeyRound, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { useSeo } from '@/hooks/useSeo'
import { useSiteSettings, useSupportWhatsapp } from '@/hooks/useSiteSettings'
import { useT } from '@/i18n'
import { whatsappHref } from '@/utils/format'
import { isLebanesePhone } from '@/utils/validation'

export function ForgotPasswordPage() {
  const t = useT()
  const { settings } = useSiteSettings()
  const support = useSupportWhatsapp()
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)

  useSeo({ title: t('forgot.seoTitle'), noIndex: true })

  // Wait for the settings before deciding there is no number: the
  // environment fallback alone would bounce somebody whose number is set
  // only by an administrator.
  if (!settings && !support) return null
  if (!whatsappHref(support)) return <Navigate to="/login" replace />

  const send = () => {
    const value = phone.trim()
    if (!value) return setError(t('validation.phoneRequired'))
    if (!isLebanesePhone(value)) return setError(t('validation.phoneInvalid'))
    const href = whatsappHref(support, t('forgot.message', { phone: value }))
    if (href) window.open(href, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="container-page flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-md">
        <CardBody className="p-6 sm:p-8">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sand-100 text-brand-700">
              <KeyRound className="h-6 w-6" aria-hidden="true" />
            </span>
            <h1 className="text-2xl">{t('forgot.title')}</h1>
            <p className="mt-2 text-ink-500">{t('forgot.body')}</p>
          </div>

          <form
            className="space-y-5"
            noValidate
            onSubmit={(event) => {
              event.preventDefault()
              send()
            }}
          >
            <Field label={t('register.loginPhoneLabel')} required error={error ?? undefined}>
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  dir="ltr"
                  placeholder="03 123 456"
                  className="ltr-nums"
                  value={phone}
                  onChange={(event) => {
                    setPhone(event.target.value)
                    if (error) setError(null)
                  }}
                  invalid={Boolean(error)}
                  autoFocus
                />
              )}
            </Field>

            <Button type="submit" size="lg" block>
              <MessageCircle className="h-5 w-5" aria-hidden="true" />
              {t('forgot.send')}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm">
            <Link to="/login" className="text-brand-700 hover:underline">
              {t('forgot.back')}
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  )
}
