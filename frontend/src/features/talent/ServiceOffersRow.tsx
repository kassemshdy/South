import { useQuery } from '@tanstack/react-query'
import { MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useT } from '@/i18n'
import { publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatPrice } from '@/utils/format'

/**
 * Priced services shown like products, each with its photo, price and
 * provider (the owners' review, 12 Nov 2026). On the services page only,
 * and only while nothing is filtered, as the other rows there.
 */
export function ServiceOffersRow() {
  const t = useT()
  const cards = useQuery({
    queryKey: queryKeys.serviceOffers(8),
    queryFn: () => publicTalentApi.offers(8),
  })
  const list = cards.data ?? []
  if (list.length === 0) return null
  return (
    <section className="bg-sand-50 py-10">
      <div className="container-page">
        <h2 className="mb-5 font-display text-2xl font-bold text-ink-900 sm:text-3xl">
          {t('serviceOffersRow.title')}
        </h2>
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {list.map(({ offer, provider_name, provider_slug, location_name }) => {
            const price = formatPrice(offer.price_from, offer.currency)
            return (
              <li key={offer.id}>
                <Link
                  to={`/talent/${encodeURIComponent(provider_slug)}#services`}
                  className="flex h-full flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift"
                >
                  <img
                    src={offer.image_thumb_url ?? offer.image_url ?? ''}
                    alt=""
                    loading="lazy"
                    className="aspect-[4/3] w-full object-cover"
                  />
                  <div className="flex flex-1 flex-col gap-1 p-3">
                    <span className="font-semibold text-ink-900" dir="auto">
                      {offer.title}
                    </span>
                    {price ? (
                      <span className="ltr-nums text-sm font-bold text-brand-800">{price}</span>
                    ) : null}
                    <span className="mt-auto flex items-center gap-1 text-xs text-ink-500">
                      <span className="truncate">{provider_name}</span>
                      {location_name ? (
                        <>
                          <MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />
                          <span className="truncate">{location_name}</span>
                        </>
                      ) : null}
                    </span>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
