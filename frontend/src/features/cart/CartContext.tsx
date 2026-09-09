import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

const STORAGE_KEY = 'south.cart'
const MAX_LINES = 50
const MAX_QUANTITY = 99

export interface CartLine {
  itemId: string
  title: string
  price: string | null
  currency: string
  imageUrl: string | null
  quantity: number
}

export interface Cart {
  /**
   * Which listing the cart belongs to. One order, one owner.
   *
   * Keyed by slug rather than id because the public product payload carries
   * a slug and no id, and the order is placed by slug too — so the identity
   * the cart uses is the one every caller already has.
   */
  businessSlug: string
  businessName: string
  whatsapp: string | null
  lines: CartLine[]
}

interface CartApi {
  cart: Cart | null
  count: number
  /** Adds a line. Returns false when the cart already belongs to another
   * listing, so the caller can ask before discarding it. */
  add: (target: Omit<Cart, 'lines'>, line: CartLine) => boolean
  replaceWith: (target: Omit<Cart, 'lines'>, line: CartLine) => void
  setQuantity: (itemId: string, quantity: number) => void
  remove: (itemId: string) => void
  clear: () => void
}

const CartContext = createContext<CartApi | null>(null)

function read(): Cart | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Cart
    // Anything hand-edited or written by an older version is discarded
    // rather than trusted: a malformed cart would break the page it is
    // rendered on, and losing a cart is a smaller harm.
    if (!parsed?.businessSlug || !Array.isArray(parsed.lines)) return null
    return parsed
  } catch {
    return null
  }
}

/**
 * The cart, in the browser only.
 *
 * No account to browse or collect — the issue is explicit about that, and it
 * is the same instinct as the rest of this project: an account is a wall in
 * front of the thing someone came to do. The order becomes server state only
 * when it is submitted.
 *
 * **One business per cart.** An order spanning two shops has no meaning here
 * because one owner has to fulfil it, so adding from a second listing has to
 * be a decision rather than a silent merge — `add` refuses and the caller
 * asks.
 */
export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(read)

  useEffect(() => {
    try {
      if (cart && cart.lines.length > 0) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cart))
      } else {
        window.localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      /* private mode or blocked storage: the cart still works for this page */
    }
  }, [cart])

  const merge = useCallback((target: Omit<Cart, 'lines'>, line: CartLine, existing: Cart | null) => {
    const lines = existing?.businessSlug === target.businessSlug ? [...existing.lines] : []
    const at = lines.findIndex((entry) => entry.itemId === line.itemId)
    if (at >= 0) {
      const current = lines[at]!
      lines[at] = {
        ...current,
        quantity: Math.min(current.quantity + line.quantity, MAX_QUANTITY),
      }
    } else if (lines.length < MAX_LINES) {
      lines.push(line)
    }
    return { ...target, lines }
  }, [])

  const add = useCallback(
    (target: Omit<Cart, 'lines'>, line: CartLine) => {
      let accepted = true
      setCart((current) => {
        if (
          current &&
          current.lines.length > 0 &&
          current.businessSlug !== target.businessSlug
        ) {
          accepted = false
          return current
        }
        return merge(target, line, current)
      })
      return accepted
    },
    [merge],
  )

  const replaceWith = useCallback(
    (target: Omit<Cart, 'lines'>, line: CartLine) => {
      setCart(merge(target, line, null))
    },
    [merge],
  )

  const api = useMemo<CartApi>(
    () => ({
      cart,
      count: cart?.lines.reduce((total, line) => total + line.quantity, 0) ?? 0,
      add,
      replaceWith,
      setQuantity: (itemId, quantity) =>
        setCart((current) => {
          if (!current) return current
          const lines = current.lines
            .map((line) =>
              line.itemId === itemId
                ? { ...line, quantity: Math.max(0, Math.min(quantity, MAX_QUANTITY)) }
                : line,
            )
            .filter((line) => line.quantity > 0)
          return lines.length > 0 ? { ...current, lines } : null
        }),
      remove: (itemId) =>
        setCart((current) => {
          if (!current) return current
          const lines = current.lines.filter((line) => line.itemId !== itemId)
          return lines.length > 0 ? { ...current, lines } : null
        }),
      clear: () => setCart(null),
    }),
    [cart, add, replaceWith],
  )

  return <CartContext.Provider value={api}>{children}</CartContext.Provider>
}

export function useCart(): CartApi {
  const api = useContext(CartContext)
  if (!api) throw new Error('useCart must be used inside CartProvider')
  return api
}
