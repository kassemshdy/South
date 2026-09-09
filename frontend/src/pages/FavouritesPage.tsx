import { Heart } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { FavouriteCard } from '@/features/favourites/FavouriteCard'
import { useFavourites } from '@/features/favourites/FavouritesContext'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/**
 * The saved list.
 *
 * Deliberately not indexed: it is one person's browser state, the same for
 * nobody else, and a search result leading here would be empty for whoever
 * clicked it.
 */
export function FavouritesPage() {
  const t = useT()
  const { favourites, clear } = useFavourites()

  useSeo({
    title: `${t('favourites.title')} | ${t('app.name')}`,
    description: t('favourites.intro'),
    noIndex: true,
  })

  return (
    <div className="container-page py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 sm:text-3xl">
            {t('favourites.title')}
          </h1>
          <p className="mt-1.5 text-ink-500">{t('favourites.intro')}</p>
        </div>
        {favourites.length > 0 ? (
          <Button variant="ghost" onClick={clear}>
            {t('favourites.clear')}
          </Button>
        ) : null}
      </header>

      {favourites.length === 0 ? (
        <div className="mt-10 rounded-2xl border-2 border-dashed border-ink-100 p-10 text-center">
          <Heart className="mx-auto h-10 w-10 text-sand-500" aria-hidden="true" />
          <p className="mt-4 font-bold text-ink-900">{t('favourites.empty')}</p>
          <p className="mt-1.5 text-ink-500">{t('favourites.emptyHint')}</p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <Button asChild>
              <Link to="/businesses">{t('favourites.browseBusinesses')}</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/products">{t('favourites.browseProducts')}</Link>
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-8 space-y-3">
          {favourites.map((favourite) => (
            <FavouriteCard
              key={`${favourite.subject}:${favourite.slug}`}
              favourite={favourite}
            />
          ))}
        </div>
      )}
    </div>
  )
}
