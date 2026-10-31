import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, RefreshCw, Store, Unplug } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * The shop's own Shopify store: connect it, see what was sent, and give it a
 * janoubona.net address.
 *
 * Hidden entirely while the integration is not configured on the server,
 * which answers 404 -- the same "inert without its variable" rule as every
 * other integration. Connecting is a full navigation to Shopify and back;
 * the callback returns here with `?shopify=connected` or an error code.
 */
export function ShopifyCard({ businessId }: { businessId: string }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [shop, setShop] = useState('')
  const [subdomain, setSubdomain] = useState('')

  const status = useQuery({
    queryKey: queryKeys.shopify(businessId),
    queryFn: () => ownerApi.shopify(businessId),
    retry: false,
    // Pushes happen in the background; keep the counts honest while any wait.
    refetchInterval: (query) => ((query.state.data?.pending_pushes ?? 0) > 0 ? 10_000 : false),
  })

  useEffect(() => {
    const outcome = params.get('shopify')
    if (!outcome) return
    if (outcome === 'connected') toast.success(t('shopify.result.connected'))
    else toast.error(t('shopify.result.failed'))
    params.delete('shopify')
    setParams(params, { replace: true })
  }, [params, setParams, toast, t])

  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.shopify(businessId) })
  const failed = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const install = useMutation({
    mutationFn: () => ownerApi.shopifyInstall(businessId, shop),
    onSuccess: ({ authorize_url }) => window.location.assign(authorize_url),
    onError: failed,
  })
  const sync = useMutation({
    mutationFn: () => ownerApi.shopifySync(businessId),
    onSuccess: () => {
      toast.success(t('shopify.syncQueued'))
      refresh()
    },
    onError: failed,
  })
  const disconnect = useMutation({
    mutationFn: () => ownerApi.shopifyDisconnect(businessId),
    onSuccess: refresh,
    onError: failed,
  })
  const saveSubdomain = useMutation({
    mutationFn: () => ownerApi.shopifySubdomain(businessId, subdomain),
    onSuccess: (data) => queryClient.setQueryData(queryKeys.shopify(businessId), data),
    onError: failed,
  })

  if (status.isError && status.error instanceof ApiError && status.error.status === 404) return null
  if (!status.data) return null
  const data = status.data

  const onConnect = (event: FormEvent) => {
    event.preventDefault()
    if (shop.trim()) install.mutate()
  }
  const onSubdomain = (event: FormEvent) => {
    event.preventDefault()
    if (subdomain.trim()) saveSubdomain.mutate()
  }

  return (
    <Card className="mb-6">
      <CardBody className="space-y-4">
        <header className="flex items-start gap-3">
          <Store className="mt-1 h-5 w-5 shrink-0 text-brand-700" aria-hidden="true" />
          <div>
            <h2 className="text-xl">{t('shopify.cardTitle')}</h2>
            <p className="mt-1 text-sm text-ink-500">{t('shopify.cardIntro')}</p>
          </div>
        </header>

        {data.connected && data.shop_domain ? (
          <div className="space-y-3">
            <p className="font-semibold text-ink-900">
              <span dir="ltr">{t('shopify.connected', { shop: data.shop_domain })}</span>
            </p>
            <ul className="space-y-1 text-sm text-ink-700">
              <li>{t('shopify.synced', { count: data.synced_products })}</li>
              {data.pending_pushes > 0 ? (
                <li>{t('shopify.pending', { count: data.pending_pushes })}</li>
              ) : null}
              {data.last_error ? (
                <li className="text-clay-700">{t('shopify.lastError', { error: data.last_error })}</li>
              ) : null}
            </ul>
            <div className="flex flex-wrap gap-2">
              {data.storefront_url ? (
                <Button asChild variant="outline" size="sm">
                  <a href={data.storefront_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    {t('shopify.storefront')}
                  </a>
                </Button>
              ) : null}
              <Button variant="outline" size="sm" onClick={() => sync.mutate()} disabled={sync.isPending}>
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {t('shopify.syncNow')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={disconnect.isPending}
                onClick={() => {
                  if (window.confirm(t('shopify.disconnectConfirm'))) disconnect.mutate()
                }}
              >
                <Unplug className="h-4 w-4" aria-hidden="true" />
                {t('shopify.disconnect')}
              </Button>
            </div>

            {data.subdomains_available ? (
              <div className="space-y-2 border-t border-ink-100 pt-4">
                {data.subdomain_hostname ? (
                  <p className="text-sm text-ink-700">
                    {data.subdomain_live
                      ? t('shopify.subdomainLive', { host: data.subdomain_hostname })
                      : t('shopify.subdomainStep', { host: data.subdomain_hostname })}
                  </p>
                ) : null}
                <form onSubmit={onSubdomain} className="flex flex-wrap items-end gap-2">
                  <Field
                    label={t('shopify.subdomainLabel', { base: data.subdomain_base })}
                    className="min-w-48 flex-1"
                  >
                    {(field) => (
                      <Input
                        {...field}
                        dir="ltr"
                        value={subdomain}
                        placeholder={data.subdomain ?? ''}
                        onChange={(event) => setSubdomain(event.target.value.toLowerCase())}
                        maxLength={31}
                      />
                    )}
                  </Field>
                  <Button type="submit" size="md" disabled={saveSubdomain.isPending}>
                    {t('shopify.subdomainSave')}
                  </Button>
                </form>
              </div>
            ) : null}
          </div>
        ) : (
          <form onSubmit={onConnect} className="space-y-3">
            {/* Shopify has no API that creates stores, so a shop without one
                is sent to sign up (through our referral link) and comes back. */}
            {data.status !== 'UNINSTALLED' ? (
              <div className="space-y-2 rounded-xl bg-sand-50 p-4">
                <p className="font-semibold text-ink-900">{t('shopify.noStoreTitle')}</p>
                <ol className="list-decimal space-y-1 ps-5 text-sm text-ink-700">
                  <li>{t('shopify.step1')}</li>
                  <li>{t('shopify.step2')}</li>
                  <li>{t('shopify.step3')}</li>
                </ol>
                {data.signup_url ? (
                  <Button asChild variant="outline" size="sm">
                    <a href={data.signup_url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" aria-hidden="true" />
                      {t('shopify.createStore')}
                    </a>
                  </Button>
                ) : null}
              </div>
            ) : null}
            {data.status === 'UNINSTALLED' ? (
              <p className="text-sm text-clay-700">{t('shopify.uninstalled')}</p>
            ) : null}
            <Field label={t('shopify.shopLabel')} hint={t('shopify.shopHint')}>
              {(field) => (
                <Input
                  {...field}
                  dir="ltr"
                  value={shop}
                  onChange={(event) => setShop(event.target.value)}
                  autoComplete="off"
                />
              )}
            </Field>
            <Button type="submit" disabled={install.isPending || !shop.trim()}>
              {t('shopify.connect')}
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  )
}
