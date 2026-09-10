import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

const STORAGE_KEY = 'south.favourites'

/**
 * A ceiling, for the same reason the cart has one: a stuck loop or a bored
 * tester should not be able to fill someone's storage quota. Generous enough
 * that nobody browsing normally will meet it.
 */
const MAX_FAVOURITES = 100

export type FavouriteSubject = 'BUSINESS' | 'TALENT' | 'PRODUCT'

const SUBJECTS: readonly FavouriteSubject[] = ['BUSINESS', 'TALENT', 'PRODUCT']

export interface Favourite {
  subject: FavouriteSubject
  slug: string
  /**
   * Enough to draw the card before the network answers — and deliberately
   * **not** the price.
   *
   * A title and a photo that are a few days stale are a cosmetic problem; a
   * price that is stale is a promise to someone that the owner never made.
   * So identity is remembered here and money is always read from the server,
   * which also means a listing whose price changed self-heals on the next
   * visit instead of quietly lying.
   */
  title: string
  imageUrl: string | null
  /** ISO timestamp. Only used to keep the newest first. */
  savedAt: string
}

/** What `toggle` did, so the caller can say something useful about it. */
export type ToggleResult = 'saved' | 'removed' | 'full'

interface FavouritesApi {
  favourites: Favourite[]
  count: number
  isFavourite: (subject: FavouriteSubject, slug: string) => boolean
  /** Saves if absent, removes if present. `'full'` means the cap was reached
   * and nothing changed. */
  toggle: (entry: Omit<Favourite, 'savedAt'>) => ToggleResult
  remove: (subject: FavouriteSubject, slug: string) => void
  /**
   * Correct a stored snapshot from a listing that was just fetched, so a
   * renamed listing or a replaced photo stops being wrong. A no-op when
   * nothing actually differs, because this is called from a render effect.
   */
  refresh: (
    subject: FavouriteSubject,
    slug: string,
    snapshot: { title: string; imageUrl: string | null },
  ) => void
  clear: () => void
}

const FavouritesContext = createContext<FavouritesApi | null>(null)

function isFavouriteEntry(value: unknown): value is Favourite {
  if (typeof value !== 'object' || value === null) return false
  const entry = value as Partial<Favourite>
  return (
    typeof entry.slug === 'string' &&
    entry.slug.length > 0 &&
    typeof entry.title === 'string' &&
    typeof entry.savedAt === 'string' &&
    (entry.imageUrl === null || typeof entry.imageUrl === 'string') &&
    SUBJECTS.includes(entry.subject as FavouriteSubject)
  )
}

function read(): Favourite[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    // Bad entries are dropped one at a time rather than the whole list being
    // thrown away, which is the difference from the cart: a cart is one
    // coherent order and half of it is meaningless, while a list of saved
    // listings is still useful with one line missing.
    return parsed.filter(isFavouriteEntry).slice(0, MAX_FAVOURITES)
  } catch {
    return []
  }
}

function same(entry: Favourite, subject: FavouriteSubject, slug: string) {
  return entry.subject === subject && entry.slug === slug
}

/**
 * Listings someone wants to come back to, in their browser only.
 *
 * No account, no table, no endpoint. The audit that asked for this described
 * someone in Beirut who found a jar of pickled olives she wanted: she could
 * share it, order it and praise it, and the one thing she could not do was
 * keep it. Putting an account in front of that would lose more people than
 * the feature gains.
 *
 * Nothing here reaches the server, so this is not analytics and no owner sees
 * a count of it. That is a deliberate line: a page view is anonymous by
 * construction, but "who saved my shop" is a fact about a person, and the
 * view counter's rule — that the database learns nothing about a visitor —
 * would not survive being bent for this.
 */
export function FavouritesProvider({ children }: { children: ReactNode }) {
  const [favourites, setFavourites] = useState<Favourite[]>(read)

  useEffect(() => {
    try {
      if (favourites.length > 0) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(favourites))
      } else {
        window.localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      /* private mode or blocked storage: the list still works for this page */
    }
  }, [favourites])

  const toggle = useCallback((entry: Omit<Favourite, 'savedAt'>) => {
    let result: ToggleResult = 'saved'
    setFavourites((current) => {
      const existing = current.findIndex((saved) => same(saved, entry.subject, entry.slug))
      if (existing >= 0) {
        result = 'removed'
        return current.filter((_, at) => at !== existing)
      }
      if (current.length >= MAX_FAVOURITES) {
        result = 'full'
        return current
      }
      result = 'saved'
      // Newest first: the reason to save something is usually to act on it
      // soon.
      return [{ ...entry, savedAt: new Date().toISOString() }, ...current]
    })
    return result
  }, [])

  const refresh = useCallback(
    (
      subject: FavouriteSubject,
      slug: string,
      snapshot: { title: string; imageUrl: string | null },
    ) => {
      setFavourites((current) => {
        const at = current.findIndex((saved) => same(saved, subject, slug))
        if (at < 0) return current
        const entry = current[at]!
        if (entry.title === snapshot.title && entry.imageUrl === snapshot.imageUrl) {
          return current
        }
        const next = [...current]
        next[at] = { ...entry, ...snapshot }
        return next
      })
    },
    [],
  )

  const api = useMemo<FavouritesApi>(
    () => ({
      favourites,
      count: favourites.length,
      isFavourite: (subject, slug) =>
        favourites.some((saved) => same(saved, subject, slug)),
      toggle,
      remove: (subject, slug) =>
        setFavourites((current) =>
          current.filter((saved) => !same(saved, subject, slug)),
        ),
      refresh,
      clear: () => setFavourites([]),
    }),
    [favourites, toggle, refresh],
  )

  return <FavouritesContext.Provider value={api}>{children}</FavouritesContext.Provider>
}

export function useFavourites(): FavouritesApi {
  const api = useContext(FavouritesContext)
  if (!api) throw new Error('useFavourites must be used inside FavouritesProvider')
  return api
}
