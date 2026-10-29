/**
 * Handing an approved applicant their way in.
 *
 * There is no SMS or WhatsApp gateway, so the site cannot send anything. What
 * it can do is generate a password and let the administrator relay it from
 * their own WhatsApp — a `wa.me` link with the message already written, which
 * opens WhatsApp Web or the desktop app with the chat ready to send.
 *
 * The password is returned by the API **once** and stored there only as a
 * hash. The owners asked for it to stay on screen until it is replaced
 * (support ticket, 26 Oct 2026), so this browser keeps it in local storage
 * beside the version it was issued at, and shows it only while
 * `GET .../credentials` reports that version is still the account's: a new
 * password, the owner choosing their own, or a sign-out-everywhere retires
 * it, and a retired one is deleted. Another administrator's browser never
 * sees it. Issuing again asks first, because it ends the owner's sessions.
 *
 * Deliberately not automatic on approval: approving a listing and handing
 * somebody a credential are two decisions, and an administrator reviewing a
 * queue of twenty should make the second one on purpose.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, KeyRound, MessageCircle } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { useStaffCan } from '@/features/admin/staffAccess'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { IssuedPassword } from '@/types/api'
import { whatsappHref } from '@/utils/format'

interface IssueCredentialsCardProps {
  userId: string
  /** The account's login. Without one there is nothing to sign in with. */
  phoneNumber: string | null
  /** True for an administrator's own account, which the API refuses. */
  isAdmin?: boolean
}

const storageKey = (userId: string) => `south.issuedPassword.${userId}`

function remembered(userId: string): IssuedPassword | null {
  try {
    const raw = window.localStorage.getItem(storageKey(userId))
    return raw ? (JSON.parse(raw) as IssuedPassword) : null
  } catch {
    return null
  }
}

function remember(userId: string, issued: IssuedPassword | null) {
  try {
    if (issued) window.localStorage.setItem(storageKey(userId), JSON.stringify(issued))
    else window.localStorage.removeItem(storageKey(userId))
  } catch {
    // Storage blocked: the password is still on screen until the page closes.
  }
}

/** Fills `{phone}`, `{password}` and `{url}` in the administrator's own
 * wording; anything else in braces is left as typed. */
export function fillCredentialsMessage(
  template: string,
  values: { phone: string; password: string; url: string },
): string {
  return template.replace(/\{(phone|password|url)\}/g, (_match, name: keyof typeof values) => values[name])
}

export function IssueCredentialsCard({
  userId,
  phoneNumber,
  isAdmin = false,
}: IssueCredentialsCardProps) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const allowed = useStaffCan('credentials')
  const [issued, setIssued] = useState<IssuedPassword | null>(null)
  const [copied, setCopied] = useState(false)
  // Replacing a password signs the owner out, so it takes two deliberate
  // steps: open the warning, then confirm inside it. A browser confirm box
  // was one click to wave through (the owners' ticket, 29 Oct 2026).
  const [confirming, setConfirming] = useState(false)

  const template = useQuery({
    queryKey: queryKeys.adminCredentialsMessage,
    queryFn: adminApi.credentialsMessage,
    enabled: allowed && !isAdmin,
  })
  const state = useQuery({
    queryKey: queryKeys.adminCredentials(userId),
    queryFn: () => adminApi.credentialState(userId),
    enabled: allowed && !isAdmin && phoneNumber !== null,
  })

  // Show the remembered password only while the account still carries the
  // version it was issued at; forget it once it has been replaced.
  useEffect(() => {
    if (!state.data) return
    const saved = remembered(userId)
    if (saved && saved.version === state.data.version) setIssued(saved)
    else if (saved) remember(userId, null)
  }, [state.data, userId])

  const issue = useMutation({
    mutationFn: () => adminApi.issueCredentials(userId),
    onSuccess: (result) => {
      setConfirming(false)
      setIssued(result)
      remember(userId, result)
      setCopied(false)
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminCredentials(userId) })
    },
    onError: (error) =>
      toast.error(
        t('credentials.failed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  if (isAdmin || !allowed) return null

  const hasPassword = Boolean(issued || state.data?.has_password)

  // A password already exists: replacing it signs the owner out, so the
  // button only opens the warning, and the warning's own button replaces it.
  const issueNew = () => {
    if (hasPassword) setConfirming(true)
    else issue.mutate()
  }

  const replaceWarning = confirming ? (
    <div className="space-y-3 rounded-xl border border-clay-200 bg-clay-50 p-3.5">
      <p className="text-sm text-clay-800">{t('credentials.reissueConfirm')}</p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => issue.mutate()} loading={issue.isPending}>
          {t('common.confirm')}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
          {t('common.cancel')}
        </Button>
      </div>
    </div>
  ) : null

  // The administrator's own wording when one is set (site settings), else
  // the site's; filled here, so the password never goes to the server.
  const values = issued
    ? { phone: issued.phone_number, password: issued.password, url: window.location.origin }
    : null
  const message = values
    ? template.data?.message
      ? fillCredentialsMessage(template.data.message, values)
      : t('credentials.whatsappMessage', values)
    : ''
  const href = issued ? whatsappHref(issued.phone_number, message) : null

  const copy = async () => {
    if (!issued) return
    try {
      await navigator.clipboard.writeText(message)
      setCopied(true)
    } catch {
      // No clipboard permission. The password is on screen either way, which
      // is why it is rendered selectable rather than masked.
      toast.error(t('credentials.copyFailed'))
    }
  }

  return (
    <Card>
      <CardBody className="space-y-4 p-5">
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-brand-700" aria-hidden="true" />
          <h2 className="font-bold">{t('credentials.heading')}</h2>
        </div>

        {phoneNumber === null ? (
          <p className="text-sm text-ink-500">{t('credentials.noPhone')}</p>
        ) : issued === null ? (
          <>
            <p className="text-sm text-ink-500">{t('credentials.explainer')}</p>
            {hasPassword ? (
              <>
                <p className="text-sm text-clay-700">{t('credentials.hasPassword')}</p>
                {replaceWarning ?? (
                  <Button variant="ghost" onClick={issueNew}>
                    {t('credentials.reissue')}
                  </Button>
                )}
              </>
            ) : (
              <Button onClick={issueNew} loading={issue.isPending}>
                {t('credentials.issue')}
              </Button>
            )}
          </>
        ) : (
          <>
            <p className="rounded-xl bg-clay-50 p-3.5 text-sm text-clay-800">
              {t('credentials.onceWarning')}
            </p>

            <dl className="space-y-2 rounded-xl border-2 border-dashed border-sand-300 bg-sand-50 p-4">
              <div>
                <dt className="text-xs text-ink-500">{t('credentials.usernameLabel')}</dt>
                <dd className="ltr-nums select-all font-semibold text-ink-900" dir="ltr">
                  {issued.phone_number}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-500">{t('credentials.passwordLabel')}</dt>
                <dd
                  className="select-all font-mono text-lg font-semibold tracking-wide text-ink-900"
                  dir="ltr"
                >
                  {issued.password}
                </dd>
              </div>
            </dl>

            <div className="flex flex-wrap gap-3">
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-olive-600 px-4 py-2.5 font-semibold text-white hover:bg-olive-700"
                >
                  <MessageCircle className="h-4 w-4" aria-hidden="true" />
                  {t('credentials.sendOnWhatsapp')}
                </a>
              ) : null}
              <Button variant="secondary" onClick={() => void copy()}>
                {copied ? (
                  <Check className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Copy className="h-4 w-4" aria-hidden="true" />
                )}
                {copied ? t('credentials.copied') : t('credentials.copyMessage')}
              </Button>
            </div>

            {replaceWarning ?? (
              <Button variant="ghost" onClick={issueNew}>
                {t('credentials.reissue')}
              </Button>
            )}
          </>
        )}
      </CardBody>
    </Card>
  )
}
