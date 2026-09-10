import { useMutation } from '@tanstack/react-query'
import { Check, MessageCircle, ShoppingBag, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { EmptyState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useCart } from '@/features/cart/CartContext'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { orderApi } from '@/services/api/endpoints'
import { useServerFieldErrors } from '@/utils/serverFieldErrors'
import { formatPrice, whatsappHref } from '@/utils/format'
import type { Currency } from '@/types/api'

/**
 * Review what was collected and ask the owner to get in touch.
 *
 * Not a checkout: there is no payment, no shipping and no stock, so the
 * total is labelled an estimate and the owner sets the real price. Calling
 * it a total without that line would be the first lie in a feature whose
 * only asset is that an owner believes what it tells them.
 *
 * After submitting, the WhatsApp handoff is offered rather than required —
 * and the hint says the order is saved either way, because it is. That is
 * the honest version of "no notification": the record exists, and the
 * message is what makes it fast.
 */
export function CartPage() {
  const t = useT()
  const toast = useToast()
  const { cart, setQuantity, remove, clear } = useCart()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [note, setNote] = useState('')
  const { fieldErrors, showErrorsFrom, clearFieldErrors } = useServerFieldErrors()
  const [sent, setSent] = useState<{ whatsapp: string | null } | null>(null)

  useSeo({ title: t('cart.title'), noIndex: true })

  const place = useMutation({
    mutationFn: () => {
      if (!cart) throw new Error('no cart')
      return orderApi.place(cart.businessSlug, {
        customer_name: name,
        customer_phone: phone,
        note: note.trim() || undefined,
        lines: cart.lines.map((line) => ({ item_id: line.itemId, quantity: line.quantity })),
      })
    },
    onSuccess: (result) => {
      const summary = (cart?.lines ?? [])
        .map((line) => `• ${line.title} × ${line.quantity}`)
        .join('\n')
      const message = t('cart.whatsappMessage', { lines: summary })
      setSent({ whatsapp: whatsappHref(cart?.whatsapp ?? null, message) })
      // Cleared only after the server accepted it, so a failed submission
      // never costs someone the list they built.
      clear()
      toast.success(t('cart.sentTitle'), result.message)
    },
    onError: (error) => {
      // Per-field sentences from the 422 land on the inputs; the envelope
      // still goes to the toast so a failure is visible even off-screen.
      showErrorsFrom(error)
      toast.error(
        t('cart.sendFailed'),
        error instanceof ApiError ? error.message : undefined,
      )
    },
  })

  if (sent) {
    return (
      <div className="container-page max-w-lg py-10">
        <div className="rounded-2xl border-2 border-olive-200 bg-olive-50 p-6">
          <Check className="h-7 w-7 text-olive-700" aria-hidden="true" />
          <h1 className="mt-2 text-2xl">{t('cart.sentTitle')}</h1>
          {sent.whatsapp ? (
            <>
              <div className="mt-4">
                <Button asChild>
                  <a href={sent.whatsapp} target="_blank" rel="noreferrer noopener">
                    <MessageCircle className="h-5 w-5" aria-hidden="true" />
                    {t('cart.sentWhatsapp')}
                  </a>
                </Button>
              </div>
              <p className="mt-2.5 text-sm text-olive-800">{t('cart.sentWhatsappHint')}</p>
            </>
          ) : null}
        </div>
      </div>
    )
  }

  if (!cart || cart.lines.length === 0) {
    return (
      <div className="container-page py-10">
        <h1 className="mb-6 text-3xl">{t('cart.title')}</h1>
        <EmptyState
          icon={<ShoppingBag className="h-7 w-7" aria-hidden="true" />}
          title={t('cart.empty')}
          description={t('cart.emptyHint')}
          action={
            <Button asChild size="lg">
              <Link to="/products">{t('cart.browse')}</Link>
            </Button>
          }
        />
      </div>
    )
  }

  const total = cart.lines.reduce(
    (sum, line) => sum + (line.price ? Number(line.price) * line.quantity : 0),
    0,
  )
  const currency = (cart.lines[0]?.currency ?? 'USD') as Currency

  return (
    <div className="container-page max-w-2xl py-10">
      <h1 className="text-3xl">{t('cart.title')}</h1>
      <p className="mt-1 text-ink-500">
        <Link
          to={`/business/${encodeURIComponent(cart.businessSlug)}`}
          className="hover:underline"
        >
          {t('cart.fromBusiness', { name: cart.businessName })}
        </Link>
      </p>

      <ul className="mt-6 space-y-3">
        {cart.lines.map((line) => (
          <li
            key={line.itemId}
            className="flex items-center gap-3 rounded-xl border border-ink-100 bg-white p-3"
          >
            {line.imageUrl ? (
              <img
                src={line.imageUrl}
                alt=""
                className="h-16 w-16 shrink-0 rounded-lg object-cover"
              />
            ) : null}
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{line.title}</p>
              {line.price ? (
                <p className="text-sm text-ink-500 ltr-nums">
                  {formatPrice(line.price, line.currency as Currency)}
                </p>
              ) : null}
            </div>
            <label className="flex items-center gap-1.5 text-sm">
              <span className="sr-only">{t('cart.quantity')}</span>
              <input
                type="number"
                min={1}
                max={99}
                value={line.quantity}
                onChange={(event) => setQuantity(line.itemId, Number(event.target.value))}
                className="w-16 rounded-lg border-2 border-ink-100 p-1.5 text-center ltr-nums"
              />
            </label>
            <button
              type="button"
              onClick={() => remove(line.itemId)}
              aria-label={t('cart.remove')}
              className="rounded-lg p-2 text-ink-400 transition-colors hover:bg-clay-50 hover:text-clay-600"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>

      {total > 0 ? (
        <div className="mt-4 rounded-xl bg-sand-50 p-4">
          <p className="flex items-baseline justify-between font-bold">
            <span>{t('cart.total')}</span>
            <span className="ltr-nums">{formatPrice(total.toFixed(2), currency)}</span>
          </p>
          <p className="mt-1 text-xs text-ink-400">{t('cart.totalHint')}</p>
        </div>
      ) : null}

      <Card className="mt-6">
        <CardBody>
          <h2 className="font-bold">{t('cart.checkoutHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('cart.checkoutIntro')}</p>

          <form
            className="mt-4 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              clearFieldErrors()
              place.mutate()
            }}
          >
            <Field label={t('cart.nameLabel')} required error={fieldErrors['customer_name']}>
              {(props) => (
                <Input
                  {...props}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  invalid={Boolean(fieldErrors['customer_name'])}
                  required
                  minLength={2}
                  maxLength={80}
                />
              )}
            </Field>
            <Field label={t('cart.phoneLabel')} required error={fieldErrors['customer_phone']}>
              {(props) => (
                <Input
                  {...props}
                  type="tel"
                  inputMode="tel"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  invalid={Boolean(fieldErrors['customer_phone'])}
                  required
                  className="ltr-nums"
                />
              )}
            </Field>
            <Field label={t('cart.noteLabel')} error={fieldErrors['note']}>
              {(props) => (
                <Textarea
                  {...props}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  invalid={Boolean(fieldErrors['note'])}
                  rows={3}
                  maxLength={1000}
                />
              )}
            </Field>

            <Button type="submit" size="lg" block loading={place.isPending}>
              {t('cart.submit')}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
