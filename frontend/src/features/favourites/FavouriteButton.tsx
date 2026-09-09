import { Heart } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import {
  useFavourites,
  type Favourite,
  type FavouriteSubject,
} from '@/features/favourites/FavouritesContext'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

/**
 * Keep this listing, or stop keeping it.
 *
 * One button for all three kinds of listing, because "save this" means the
 * same thing whether the thing is a shop, a person or a jar of olives — and
 * the favourites page has to render all three from one list anyway.
 *
 * The label says saved/save rather than counting anything: nothing about this
 * reaches the server, so there is no total to show and no owner to show it
 * to.
 */
export function FavouriteButton({
  subject,
  slug,
  title,
  imageUrl,
  block = false,
  variant = 'outline',
}: Omit<Favourite, 'savedAt'> & {
  subject: FavouriteSubject
  block?: boolean
  variant?: 'outline' | 'ghost'
}) {
  const t = useT()
  const { isFavourite, toggle } = useFavourites()
  const { success, error, toast } = useToast()
  const saved = isFavourite(subject, slug)

  const onToggle = () => {
    const result = toggle({ subject, slug, title, imageUrl })
    if (result === 'full') {
      error(t('favourites.fullTitle'), t('favourites.fullBody'))
      return
    }
    if (result === 'saved') {
      success(t('favourites.savedTitle'), t('favourites.savedBody'))
      return
    }
    toast({ tone: 'info', title: t('favourites.removedTitle') })
  }

  return (
    <Button
      type="button"
      variant={variant}
      block={block}
      onClick={onToggle}
      aria-pressed={saved}
      title={saved ? t('favourites.remove') : t('favourites.save')}
    >
      <Heart
        className={cn('h-4 w-4', saved && 'fill-clay-500 text-clay-500')}
        aria-hidden="true"
      />
      {saved ? t('favourites.saved') : t('favourites.save')}
    </Button>
  )
}
