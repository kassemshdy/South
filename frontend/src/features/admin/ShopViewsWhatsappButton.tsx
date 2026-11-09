import { useQuery } from '@tanstack/react-query'
import { Eye } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminBusiness } from '@/types/api'
import { whatsappHref } from '@/utils/format'

/**
 * Tells a shop's owner, on WhatsApp, how many times their page and products
 * were viewed in the last 30 days, with the page's link (the owners' request,
 * 9 Nov 2026: proof is the weakest lever, and a seller who sees people
 * looking keeps going). Sent to the account number, like every staff
 * message to an owner; only for a published shop, whose link works.
 */
export function ShopViewsWhatsappButton({ business }: { business: AdminBusiness }) {
  const t = useT()
  const published = business.status === 'APPROVED'
  const views = useQuery({
    queryKey: queryKeys.adminBusinessViews(business.id),
    queryFn: () => adminApi.views(business.id),
    enabled: published,
  })
  const number = business.owner_phone ?? business.whatsapp ?? business.phone
  if (!published || !views.data) return null
  const href = whatsappHref(
    number,
    t('admin.viewsWhatsapp', {
      name: business.name,
      page: views.data.page_views,
      products: views.data.product_views,
      days: views.data.days,
      link: `${window.location.origin}/business/${business.slug}`,
    }),
  )
  if (!href) return null
  return (
    <div className="space-y-1">
      <Button asChild variant="outline" size="sm">
        <a href={href} target="_blank" rel="noopener noreferrer">
          <Eye className="h-4 w-4" aria-hidden="true" />
          {t('admin.viewsWhatsappButton')}
        </a>
      </Button>
      <p className="text-xs text-ink-500">
        {t('admin.viewsWhatsappHint', {
          page: views.data.page_views,
          products: views.data.product_views,
          days: views.data.days,
        })}
      </p>
    </div>
  )
}
