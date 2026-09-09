import { useQuery } from '@tanstack/react-query'
import { Heart, Package, Store, UserRound } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import {
  useFavourites,
  type Favourite,
  type FavouriteSubject,
} from '@/features/favourites/FavouritesContext'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { publicBusinessApi, publicItemApi, publicTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatPrice } from '@/utils/format'

/** What a card needs, whichever kind of listing it came from. */
interface Live {
  title: string
  imageUrl: string | null
  subtitle: string | null
  price: string | null
}

const ICONS: Record<FavouriteSubject, typeof Store> = {
  BUSINESS: Store,
  TALENT: UserRound,
  PRODUCT: Package,
}

function href(subject: FavouriteSubject, slug: string) {
  const path =
    subject === 'BUSINESS' ? 'business' : subject === 'TALENT' ? 'talent' : 'product'
  return `/${path}/${encodeURIComponent(slug)}`
}

/**
 * One saved listing, re-read from the API.
 *
 * The stored snapshot draws the card immediately so the page is never blank,
 * and then the server's answer replaces it. Two things fall out of that and
 * both are the point:
 *
 * - **A price only ever comes from the response.** Never from storage — see
 *   the note on `Favourite.title`.
 * - **A listing that is no longer public disappears by itself.** The public
 *   endpoints refuse anything that is not `APPROVED`, so a suspended or
 *   deleted listing answers 404 and the card says so rather than linking
 *   someone to a dead page.
 */
export function FavouriteCard({ favourite }: { favourite: Favourite }) {
  const t = useT()
  const { subject, slug } = favourite
  const { remove, refresh } = useFavourites()

  const business = useQuery({
    queryKey: queryKeys.business(slug),
    queryFn: () => publicBusinessApi.bySlug(slug),
    enabled: subject === 'BUSINESS',
  })
  const talent = useQuery({
    queryKey: queryKeys.talent(slug),
    queryFn: () => publicTalentApi.bySlug(slug),
    enabled: subject === 'TALENT',
  })
  const product = useQuery({
    queryKey: queryKeys.product(slug),
    queryFn: () => publicItemApi.bySlug(slug),
    enabled: subject === 'PRODUCT',
  })

  const query = subject === 'BUSINESS' ? business : subject === 'TALENT' ? talent : product

  let live: Live | null = null
  if (business.data && subject === 'BUSINESS') {
    live = {
      title: business.data.name,
      imageUrl: business.data.cover_url ?? business.data.logo_url,
      subtitle: business.data.short_description,
      price: null,
    }
  } else if (talent.data && subject === 'TALENT') {
    live = {
      title: talent.data.display_name,
      imageUrl: talent.data.photo_url,
      subtitle: talent.data.headline,
      price: null,
    }
  } else if (product.data && subject === 'PRODUCT') {
    live = {
      title: product.data.title,
      imageUrl: product.data.image_url,
      subtitle: product.data.business.name,
      price: formatPrice(product.data.price, product.data.currency),
    }
  }

  // Self-heal the snapshot so a renamed listing or a replaced photo stops
  // being wrong on the next visit. Depends on the values rather than on
  // `live`, which is a fresh object every render.
  const liveTitle = live?.title
  const liveImageUrl = live?.imageUrl
  useEffect(() => {
    if (liveTitle === undefined || liveImageUrl === undefined) return
    refresh(subject, slug, { title: liveTitle, imageUrl: liveImageUrl })
  }, [liveTitle, liveImageUrl, refresh, subject, slug])

  const Icon = ICONS[subject]
  const image = live?.imageUrl ?? favourite.imageUrl
  const gone = query.isError && query.error instanceof ApiError && query.error.status === 404

  if (gone) {
    return (
      <article className="flex items-center gap-4 rounded-2xl border border-ink-100 bg-sand-50 p-5">
        <div className="min-w-0 flex-1" dir="auto">
          <p className="truncate font-bold text-ink-500 line-through">{favourite.title}</p>
          <p className="mt-1 text-sm text-ink-500">{t('favourites.gone')}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => remove(subject, slug)}>
          {t('favourites.remove')}
        </Button>
      </article>
    )
  }

  return (
    <article className="flex items-center gap-4 rounded-2xl border border-ink-100 bg-white p-5 shadow-card">
      <Link
        to={href(subject, slug)}
        className="shrink-0"
        tabIndex={-1}
        aria-hidden="true"
      >
        <div className="h-16 w-16 overflow-hidden rounded-xl bg-sand-100">
          {image ? (
            <img
              src={image}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sand-500">
              <Icon className="h-7 w-7" aria-hidden="true" />
            </div>
          )}
        </div>
      </Link>

      {/* dir="auto" so owner-authored content keeps its own direction
          regardless of the UI language, as the directory cards do. */}
      <div className="min-w-0 flex-1" dir="auto">
        <h3 className="truncate text-lg font-bold text-ink-900">
          <Link to={href(subject, slug)} className="transition-colors hover:text-clay-600">
            {live?.title ?? favourite.title}
          </Link>
        </h3>
        {live?.subtitle ? (
          <p className="mt-0.5 truncate text-sm text-ink-500">{live.subtitle}</p>
        ) : null}
        {/* Absent until the server answers, rather than shown from storage:
            a stale price is a promise the owner never made. */}
        {query.isLoading && subject === 'PRODUCT' ? (
          <Skeleton className="mt-1.5 h-4 w-20" />
        ) : live?.price ? (
          <p className="ltr-nums mt-1 text-sm font-bold text-clay-700">{live.price}</p>
        ) : null}
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={() => remove(subject, slug)}
        aria-label={t('favourites.remove')}
        title={t('favourites.remove')}
      >
        <Heart className="h-5 w-5 fill-clay-500 text-clay-500" aria-hidden="true" />
      </Button>
    </article>
  )
}
