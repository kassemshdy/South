import { MapPin, MessageCircle, Phone, Store } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useT } from '@/i18n'
import type { BusinessSummary } from '@/types/api'
import { telHref, whatsappHref } from '@/utils/format'

export function BusinessCard({ business }: { business: BusinessSummary }) {
  const t = useT()
  const profileUrl = `/business/${encodeURIComponent(business.slug)}`
  const whatsapp = whatsappHref(
    business.whatsapp,
    t('business.whatsappMessage', { name: business.name }),
  )
  const phone = telHref(business.phone)

  return (
    <article className="group flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lift">
      <Link to={profileUrl} className="block" tabIndex={-1} aria-hidden="true">
        <div className="relative h-36 overflow-hidden bg-sand-100">
          {business.cover_url ? (
            <img
              src={business.cover_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sand-500">
              <Store className="h-10 w-10" aria-hidden="true" />
            </div>
          )}
          {business.logo_url ? (
            <img
              src={business.logo_url}
              alt=""
              loading="lazy"
              className="absolute bottom-3 start-4 h-14 w-14 rounded-xl border-2 border-white object-cover shadow-card"
            />
          ) : null}
        </div>
      </Link>

      {/* dir="auto" so an Arabic listing still reads right-to-left on an
          English page, and an English one reads left-to-right on an Arabic
          page: owner-authored content carries its own direction, independent
          of the UI language. */}
      <div className="flex flex-1 flex-col p-5" dir="auto">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {business.category ? (
            <Badge className="bg-sand-100 text-brand-700">{business.category.name_ar}</Badge>
          ) : null}
          {business.location ? (
            <span className="inline-flex items-center gap-1 text-xs text-ink-500">
              <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
              {business.location.name_ar}
            </span>
          ) : null}
        </div>

        <h3 className="text-lg font-bold text-ink-900">
          <Link to={profileUrl} className="transition-colors hover:text-brand-700">
            {business.name}
          </Link>
        </h3>

        {business.short_description ? (
          <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-ink-500">
            {business.short_description}
          </p>
        ) : null}

        <div className="mt-auto flex items-center gap-2 pt-4">
          <Button asChild size="sm" variant="outline" className="flex-1">
            <Link to={profileUrl}>{t('business.viewDetails')}</Link>
          </Button>
          {whatsapp ? (
            <Button
              asChild
              size="icon"
              variant="whatsapp"
              aria-label={t('business.whatsappAria', { name: business.name })}
            >
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-5 w-5" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
          {phone ? (
            <Button
              asChild
              size="icon"
              variant="outline"
              aria-label={t('business.callAria', { name: business.name })}
            >
              <a href={phone}>
                <Phone className="h-5 w-5" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
        </div>
      </div>
    </article>
  )
}
