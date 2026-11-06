import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  ExternalLink,
  ListPlus,
  Package,
  Pencil,
  Plus,
  Send,
  ShoppingBag,
  Store,
  UserRound,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { StatusBadge } from '@/features/businesses/StatusBadge'
import { useAuth } from '@/features/auth/AuthContext'
import { AiToolsSoon } from '@/features/growth/AiToolsSoon'
import { LiveSharePanel } from '@/features/insights/LiveSharePanel'
import { ViewsPanel } from '@/features/insights/ViewsPanel'
import { useSeo } from '@/hooks/useSeo'
import { useI18n, useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { insightsApi, ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { ListingViews, OwnerBusiness } from '@/types/api'
import { formatPrice, formatRelativeDate } from '@/utils/format'

/**
 * Asks for the account holder's details until they are there, then stops.
 *
 * The wizard's first step covers this, but most owners never walk the wizard
 * any more: they apply on the public form, an administrator approves it, and
 * they arrive here with a listing already made. Without this, the identity
 * fields and the photo would be asked for only on a screen those owners never
 * open — so the prompt lives where everyone lands instead.
 *
 * It renders nothing once both are filled, and it never blocks anything. A
 * listing is reviewed by a person, and chasing a photo with a modal would
 * only teach people to dismiss modals.
 */
function IdentityPrompt() {
  const { user } = useAuth()
  const t = useT()

  if (!user) return null
  const needsName = !user.full_name
  const needsPhoto = !user.photo_url
  if (!needsName && !needsPhoto) return null

  const missing = [
    needsName && t('wizard.personalMissingName'),
    needsPhoto && t('wizard.personalMissingPhoto'),
  ].filter((entry): entry is string => Boolean(entry))

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border-2 border-dashed border-sand-300 bg-sand-50 p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-brand-700">
          <UserRound className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p className="font-semibold text-ink-900">{t('dashboard.identityPromptTitle')}</p>
          <p className="mt-0.5 text-sm text-ink-500">
            {t('wizard.personalMissing', {
              fields: missing.join(t('common.listSeparator')),
            })}
          </p>
        </div>
      </div>
      <Button asChild variant="outline">
        <Link to="/dashboard/account">{t('wizard.personalEdit')}</Link>
      </Button>
    </div>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const t = useT()
  useSeo({ title: t('dashboard.seoTitle'), noIndex: true })

  const businesses = useQuery({ queryKey: queryKeys.myBusinesses, queryFn: ownerApi.list })
  // One request for every card, rather than one per card. It is allowed to
  // fail quietly: a dashboard without its numbers is still a dashboard, and
  // the panel renders its "no views yet" state.
  const views = useQuery({ queryKey: queryKeys.myViews, queryFn: insightsApi.myViews })
  const viewsById = new Map<string, ListingViews>(
    (views.data?.listings ?? []).map((entry) => [entry.subject_id, entry]),
  )

  return (
    <div className="container-page py-10">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{t('dashboard.heading')}</h1>
          <p className="mt-2 text-ink-500">
            {t('dashboard.greeting', {
              name: user?.display_name ? ` ${user.display_name}` : '',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg" variant="outline">
            <Link to="/dashboard/talent">
              <UserRound className="h-5 w-5" aria-hidden="true" />
              {t('dashboard.myTalentProfile')}
            </Link>
          </Button>
          <Button asChild size="lg">
            <Link to="/dashboard/businesses/new">
              <Plus className="h-5 w-5" aria-hidden="true" />
              {t('dashboard.addNew')}
            </Link>
          </Button>
        </div>
      </header>

      <IdentityPrompt />

      {businesses.isLoading ? (
        <div className="grid gap-5 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <Skeleton key={index} className="h-56 rounded-2xl" />
          ))}
        </div>
      ) : businesses.isError ? (
        <ErrorState error={businesses.error} onRetry={() => void businesses.refetch()} />
      ) : businesses.data && businesses.data.length > 0 ? (
        <div className="space-y-5">
          {businesses.data.map((business) => (
            // Each shop beside its own products, so the half of the row the
            // card used to leave empty shows what the shop actually sells.
            <div key={business.id} className="grid items-start gap-5 lg:grid-cols-2">
              <OwnerBusinessCard
                business={business}
                views={viewsById.get(business.id)}
                windowDays={views.data?.window_days ?? 14}
              />
              <OwnerProductsPanel business={business} />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Store className="h-7 w-7" aria-hidden="true" />}
          title={t('dashboard.emptyTitle')}
          description={t('dashboard.emptyDescription')}
          action={
            <Button asChild size="lg">
              <Link to="/dashboard/businesses/new">{t('nav.addBusiness')}</Link>
            </Button>
          }
        />
      )}

      <AiToolsSoon />
    </div>
  )
}

/** The most products the dashboard lists before pointing to the full page. */
const PRODUCTS_PREVIEW = 6

function OwnerProductsPanel({ business }: { business: OwnerBusiness }) {
  const t = useT()
  const itemsPath = `/dashboard/businesses/${business.id}/items`
  const shown = business.items.slice(0, PRODUCTS_PREVIEW)

  return (
    <Card>
      <CardBody>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-bold">{t('itemsPage.heading')}</h3>
          <Button asChild variant="outline" size="sm">
            <Link to={itemsPath}>
              <ListPlus className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.manageItems', { count: business.items.length })}
            </Link>
          </Button>
        </div>

        {shown.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-ink-100 p-6 text-center">
            <Package className="mx-auto h-7 w-7 text-ink-300" aria-hidden="true" />
            <p className="mt-2 font-semibold text-ink-700">{t('items.emptyTitle')}</p>
            <Button asChild size="sm" className="mt-3">
              <Link to={itemsPath}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t('items.addItem')}
              </Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-ink-100">
            {shown.map((item) => {
              const price = formatPrice(item.price, item.currency)
              return (
                <li key={item.id}>
                  <Link
                    to={itemsPath}
                    className={`flex items-center gap-3 py-2.5 hover:text-brand-700 ${item.is_available ? '' : 'opacity-60'}`}
                  >
                    <span className="h-12 w-12 shrink-0 overflow-hidden rounded-lg bg-sand-100">
                      {item.image_url ? (
                        <img src={item.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />
                      ) : (
                        <span className="flex h-full items-center justify-center text-sand-500">
                          <Package className="h-5 w-5" aria-hidden="true" />
                        </span>
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold">{item.title}</span>
                      {!item.is_available ? (
                        <span className="block text-xs text-ink-500">{t('items.unavailable')}</span>
                      ) : null}
                    </span>
                    {price ? (
                      <span className="ltr-nums shrink-0 text-sm font-bold text-brand-800">{price}</span>
                    ) : null}
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

function OwnerBusinessCard({
  business,
  views,
  windowDays,
}: {
  business: OwnerBusiness
  views: ListingViews | undefined
  windowDays: number
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { t, locale } = useI18n()

  const submit = useMutation({
    mutationFn: () => ownerApi.submit(business.id),
    onSuccess: () => {
      toast.success(t('dashboard.submitted'), t('dashboard.submittedDescription'))
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
    },
    onError: (error) => {
      // A 422 lists the fields the owner still needs to fill in.
      const message = error instanceof ApiError ? error.message : t('dashboard.submitFailed')
      toast.error(t('dashboard.submitBlocked'), message)
    },
  })

  const canSubmit = business.status === 'DRAFT' || business.status === 'REJECTED'

  return (
    <Card className="flex flex-col">
      <CardBody className="flex flex-1 flex-col">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-sand-100">
            {business.logo_url ? (
              <img src={business.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-sand-500">
                <Store className="h-7 w-7" aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold">{business.name}</h2>
              <StatusBadge status={business.status} />
            </div>
            <p className="mt-1 text-sm text-ink-500">
              {business.custom_category_text || business.category?.name_ar || t('dashboard.noCategory')}
              {business.location ? ` · ${business.location.name_ar}` : ''}
            </p>
            <p className="mt-0.5 text-xs text-ink-300">
              {t('dashboard.lastUpdated', {
                date: formatRelativeDate(business.updated_at, locale, t),
              })}
            </p>
          </div>
        </div>

        {business.status === 'REJECTED' && business.rejection_reason ? (
          <div className="mt-4 flex gap-2.5 rounded-xl border-2 border-clay-200 bg-clay-50 p-3.5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-clay-900">{t('dashboard.needsChanges')}</p>
              <p className="mt-0.5 text-sm leading-relaxed text-clay-700">{business.rejection_reason}</p>
            </div>
          </div>
        ) : null}

        {business.status === 'PENDING_REVIEW' ? (
          <p className="mt-4 rounded-xl bg-sand-100 p-3.5 text-sm text-clay-800">
            {t('dashboard.pendingNotice')}
          </p>
        ) : null}

        {business.status === 'SUSPENDED' ? (
          <p className="mt-4 rounded-xl bg-ink-100 p-3.5 text-sm text-ink-700">
            {t('dashboard.suspendedNotice')}
          </p>
        ) : null}

        {business.status === 'APPROVED' ? (
          <>
            <LiveSharePanel
              name={business.name}
              path={`/business/${encodeURIComponent(business.slug)}`}
            />
            <ViewsPanel views={views} windowDays={windowDays} />
          </>
        ) : null}

        <div className="mt-5 flex flex-wrap gap-2 pt-1">
          <Button asChild variant="outline" size="sm">
            <Link to={`/dashboard/businesses/${business.id}/edit`}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.editBusiness')}
            </Link>
          </Button>

          <Button asChild variant="outline" size="sm">
            <Link to={`/dashboard/businesses/${business.id}/items`}>
              <ListPlus className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.manageItems', { count: business.items.length })}
            </Link>
          </Button>

          {/* Orders used to be one tab deep in the edit page, where an owner
              had to already know to look. The count is of new ones only:
              what is waiting for a reply. */}
          <Button asChild variant={business.new_orders > 0 ? 'primary' : 'outline'} size="sm">
            <Link to={`/dashboard/businesses/${business.id}/edit?tab=orders`}>
              <ShoppingBag className="h-4 w-4" aria-hidden="true" />
              {t('wizard.stepOrders')}
              {business.new_orders > 0 ? (
                <span
                  className="ms-1 rounded-full bg-white px-1.5 text-xs font-bold text-brand-800 ltr-nums"
                  aria-label={t('dashboard.newOrders', { count: business.new_orders })}
                >
                  {business.new_orders}
                </span>
              ) : null}
            </Link>
          </Button>

          {business.status === 'APPROVED' ? (
            <Button asChild variant="ghost" size="sm">
              <Link to={`/business/${encodeURIComponent(business.slug)}`}>
                <ExternalLink className="h-4 w-4" aria-hidden="true" />
                {t('dashboard.publicPage')}
              </Link>
            </Button>
          ) : null}

          {canSubmit ? (
            <Button size="sm" loading={submit.isPending} onClick={() => submit.mutate()}>
              <Send className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.submitForReview')}
            </Button>
          ) : null}
        </div>

        {canSubmit && submit.error instanceof ApiError && submit.error.missing.length > 0 ? (
          <div className="mt-3 rounded-xl border border-sand-300 bg-sand-50 p-3">
            <p className="text-sm font-semibold text-clay-800">
              {t('dashboard.completeFirst')}
            </p>
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {submit.error.missing.map((item) => (
                <li key={item}>
                  {/* The API returns catalog keys, not sentences, so the
                      reader's locale decides the wording. */}
                  <Badge className="bg-white text-clay-700">{t(item as TranslationKey)}</Badge>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardBody>
    </Card>
  )
}
