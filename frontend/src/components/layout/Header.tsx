import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import {
  ChevronDown,
  Heart,
  LayoutDashboard,
  LogOut,
  Menu,
  Languages,
  Search,
  ShoppingBag,
  Shield,
  User,
  UserCog,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { LocaleToggle, useLocaleSwitch } from '@/components/layout/LocaleToggle'
import { SITE_SECTIONS } from '@/components/layout/navigation'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { useCart } from '@/features/cart/CartContext'
import { useFavourites } from '@/features/favourites/FavouritesContext'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

/**
 * The header holds the same number of things whether or not anybody is signed
 * in.
 *
 * It used to grow: signing in appended `nav.myBusinesses`, `nav.account` and
 * a sign-out button, plus `nav.adminPanel` for an admin, so the people who use
 * the site most got the most crowded bar — eight items and a call to action
 * competing on one line. Everything personal lives behind one account menu
 * regardless of sign-in state.
 *
 * The public side is the headings the directory's owner asked for, in their
 * order, each a direct link: products, services and skills, news, the blog,
 * about us. They were briefly grouped — three visible and three behind a
 * `nav.more` menu — to keep the row short; that was overruled, because a
 * heading somebody has to find is not a heading.
 *
 * `nav.more` came back for what is *not* a heading. The language switch lives
 * there rather than in the row, because a button wide enough to carry the
 * word «English» costs a heading's worth of width and is touched once.
 *
 * Home is not a heading either: the logo has always gone there, and every site
 * a visitor has ever used taught them that.
 *
 * Long headings need the width all the same — two of them are three words —
 * so the row appears at `xl` rather than the `md` three short links used to
 * need, and the drawer covers everything narrower. Measured rather than
 * guessed, and re-measured after the language switch moved into the menu:
 * the row still overflows its container at 1024, where the sign-in button is
 * the first thing pushed off the edge.
 *
 * The business directory is not one of the six. It keeps a home in the bar as
 * the search icon, which is where it already lived at narrow widths, and in
 * the footer — a directory nobody can reach from the header of a directory
 * site would be a strange thing to ship.
 *
 * Signed out the bar ends in one button, `nav.login`. Signed in it ends in
 * the account menu and nothing after it. It used to end in `nav.addBusiness`
 * either way, which was wrong twice over: signed out it told a craftsperson,
 * a customer and a shopkeeper alike that the thing to do here is open a
 * shop, and signed in it sat beside the account menu so the bar appeared to
 * offer a way in and a way further in at once. Adding a business is a task,
 * not a greeting — the hero chooser and the dashboard both lead to it.
 *
 * (Key names rather than the strings themselves: `tests/test_i18n.py` scans
 * this directory for Arabic codepoints, comments included.)
 */

// `whitespace-nowrap` is load-bearing with six headings in the row: two of
// them are three words long, and left to wrap they turn a 64px bar into a
// two-line one. Padding stays tight until there is room to spare.
const NAV_LINK =
  'whitespace-nowrap rounded-lg px-2.5 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900 2xl:px-3'

const MENU_ITEM =
  'flex cursor-pointer select-none items-center gap-2.5 rounded-lg px-3 py-2.5 text-[15px] text-ink-700 outline-none data-[highlighted]:bg-sand-100 data-[highlighted]:text-ink-900'

function CartLink() {
  const t = useT()
  const { count } = useCart()

  // Absent when empty rather than showing a zero: a permanent cart icon on a
  // directory suggests a shop, and this is only a shop once someone has put
  // something in it.
  if (count === 0) return null

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      // Icon alone, at every width. The count badge is the label that
      // matters — it says there is something waiting — and the word beside
      // it bought nothing the bag and the number did not already say, while
      // widening the row it shares with the account menu. `title` is the
      // pointer affordance and `aria-label` the assistive one; both carry
      // the same string, so neither audience is guessing at a glyph.
      title={t('cart.link')}
      aria-label={t('cart.link')}
    >
      <Link to="/cart" className="relative">
        <ShoppingBag className="h-5 w-5" aria-hidden="true" />
        <span className="absolute -end-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-clay-500 px-1 text-[10px] font-bold text-white ltr-nums">
          {count}
        </span>
      </Link>
    </Button>
  )
}

function FavouritesLink() {
  const t = useT()
  const { count } = useFavourites()

  // Same rule as the cart: absent until there is something in it. A heart on
  // an empty list is a feature advertising itself rather than a way back to
  // something someone chose. Icon-only for the same reason as the cart.
  if (count === 0) return null

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      title={t('favourites.link')}
      aria-label={t('favourites.link')}
    >
      <Link to="/favourites" className="relative">
        <Heart className="h-5 w-5" aria-hidden="true" />
        <span className="absolute -end-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-clay-500 px-1 text-[10px] font-bold text-white ltr-nums">
          {count}
        </span>
      </Link>
    </Button>
  )
}

/**
 * The row's overflow: what belongs in the header without belonging beside the
 * headings.
 *
 * The language switch is the whole of it today. It used to sit in the row as
 * a button wide enough to carry the word «English», which is a lot of width
 * for something most visitors touch once and never again, and the headings
 * need that width more than it does.
 */
function MoreMenu() {
  const t = useT()
  const { label, action, switchLocale } = useLocaleSwitch()

  return (
    <DropdownMenuPrimitive.Root>
      <DropdownMenuPrimitive.Trigger asChild>
        <button type="button" className={cn(NAV_LINK, 'flex items-center gap-1')}>
          {t('nav.more')}
          <ChevronDown className="h-3.5 w-3.5 text-ink-500" aria-hidden="true" />
        </button>
      </DropdownMenuPrimitive.Trigger>
      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-48 overflow-hidden rounded-xl border border-ink-100 bg-white p-1 shadow-lift"
        >
          <DropdownMenuPrimitive.Item
            className={MENU_ITEM}
            onSelect={switchLocale}
            aria-label={action}
          >
            <Languages className="h-4 w-4 text-ink-500" aria-hidden="true" />
            {label}
          </DropdownMenuPrimitive.Item>
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  )
}

export function Header() {
  const { isAuthenticated, isAdmin, user, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const t = useT()

  const handleSignOut = () => {
    signOut()
    setMenuOpen(false)
    navigate('/')
  }

  const account = user?.phone_number ?? user?.email

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-sand-50/95 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2.5 whitespace-nowrap font-display text-lg font-bold text-ink-900"
        >
          {/* The real mark, not a stand-in glyph. Round rather than the
              rounded square the placeholder used: the emblem is a circle, and
              a circular frame crops only the white it was padded with. */}
          <img
            src="/janoubna-mark.png"
            alt=""
            width={36}
            height={36}
            className="h-9 w-9 shrink-0 rounded-full bg-white object-cover"
          />
          {t('app.name')}
        </Link>

        <nav className="hidden items-center gap-1 xl:flex" aria-label={t('nav.mainAria')}>
          {SITE_SECTIONS.map((section) => (
            <Link key={section.href} to={section.href} className={NAV_LINK}>
              {t(section.labelKey)}
            </Link>
          ))}

          {/* The directory, as an icon rather than a seventh heading: the six
              above are the ones that were asked for, and this is the same
              control the narrow bar has carried all along. */}
          <Button asChild variant="ghost" size="icon" aria-label={t('nav.searchAria')}>
            <Link to="/businesses">
              <Search className="h-5 w-5" aria-hidden="true" />
            </Link>
          </Button>

          <MoreMenu />

          {/* One control, either way: a sign-in link or the account menu. The
              row never gains an item for being signed in. */}
          {isAuthenticated ? (
            <DropdownMenuPrimitive.Root>
              <DropdownMenuPrimitive.Trigger asChild>
                <Button variant="ghost" size="sm" aria-label={t('nav.accountMenuAria')}>
                  <User className="h-4 w-4" aria-hidden="true" />
                  <ChevronDown className="h-3.5 w-3.5 text-ink-500" aria-hidden="true" />
                </Button>
              </DropdownMenuPrimitive.Trigger>

              <DropdownMenuPrimitive.Portal>
                <DropdownMenuPrimitive.Content
                  align="end"
                  sideOffset={6}
                  className="z-50 min-w-56 overflow-hidden rounded-xl border border-ink-100 bg-white p-1 shadow-lift"
                >
                  {account ? (
                    <DropdownMenuPrimitive.Label className="px-3 pb-1.5 pt-2 text-xs text-ink-500">
                      <span className="ltr-nums inline-block">{account}</span>
                    </DropdownMenuPrimitive.Label>
                  ) : null}

                  <DropdownMenuPrimitive.Item asChild className={MENU_ITEM}>
                    <Link to="/dashboard">
                      <LayoutDashboard className="h-4 w-4 text-ink-500" aria-hidden="true" />
                      {t('nav.myBusinesses')}
                    </Link>
                  </DropdownMenuPrimitive.Item>

                  <DropdownMenuPrimitive.Item asChild className={MENU_ITEM}>
                    <Link to="/dashboard/account">
                      <UserCog className="h-4 w-4 text-ink-500" aria-hidden="true" />
                      {t('nav.account')}
                    </Link>
                  </DropdownMenuPrimitive.Item>

                  {isAdmin ? (
                    <DropdownMenuPrimitive.Item asChild className={MENU_ITEM}>
                      <Link to="/admin">
                        <Shield className="h-4 w-4 text-ink-500" aria-hidden="true" />
                        {t('nav.adminPanel')}
                      </Link>
                    </DropdownMenuPrimitive.Item>
                  ) : null}

                  <DropdownMenuPrimitive.Separator className="my-1 h-px bg-ink-100" />

                  <DropdownMenuPrimitive.Item
                    onSelect={handleSignOut}
                    className={cn(MENU_ITEM, 'text-clay-600 data-[highlighted]:bg-clay-50 data-[highlighted]:text-clay-700')}
                  >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    {t('nav.signOut')}
                  </DropdownMenuPrimitive.Item>
                </DropdownMenuPrimitive.Content>
              </DropdownMenuPrimitive.Portal>
            </DropdownMenuPrimitive.Root>
          ) : null}

          <CartLink />
          <FavouritesLink />

          {/* Signed out, one button: sign in. Signed in, none — the account
              menu above already is the control, and a second button beside
              it read as a stray "log in" next to the thing you log in to.

              It used to say "add your business" here, which told a
              craftsperson, a customer and a shopkeeper alike that the thing
              to do on this site is open a shop — the same assumption the
              hero card made. Adding a business is a task, not a greeting: it
              lives on the hero chooser and inside the dashboard, where
              someone who wants it is already looking. */}
          {isAuthenticated ? null : (
            <Button asChild size="sm" className="ms-2 shrink-0 whitespace-nowrap">
              <Link to="/login">
                <User className="h-4 w-4" aria-hidden="true" />
                {t('nav.login')}
              </Link>
            </Button>
          )}
        </nav>

        <div className="flex items-center gap-1 xl:hidden">
          <CartLink />
          <FavouritesLink />
          <LocaleToggle compact />
          <Button asChild variant="ghost" size="icon" aria-label={t('nav.searchAria')}>
            <Link to="/businesses">
              <Search className="h-5 w-5" aria-hidden="true" />
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? t('nav.closeMenu') : t('nav.openMenu')}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      <div
        id="mobile-menu"
        className={cn('border-t border-ink-100 bg-white xl:hidden', menuOpen ? 'block' : 'hidden')}
      >
        <nav className="container-page flex flex-col gap-1 py-3" aria-label={t('nav.mobileAria')}>
          {SITE_SECTIONS.map((section) => (
            <Link
              key={section.href}
              to={section.href}
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100"
            >
              {t(section.labelKey)}
            </Link>
          ))}

          {/* The drawer is already a submenu, so the personal links sit here
              under their own heading rather than behind a second tap. */}
          {isAuthenticated ? (
            <>
              <p className="mt-2 border-t border-ink-100 px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-ink-500">
                {t('nav.accountSection')}
              </p>
              {account ? (
                <p className="px-3 pb-1 text-xs text-ink-500">
                  <span className="ltr-nums inline-block">{account}</span>
                </p>
              ) : null}
              <Link to="/dashboard" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
                {t('nav.myBusinesses')}
              </Link>
              <Link to="/dashboard/account" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
                {t('nav.account')}
              </Link>
              {isAdmin ? (
                <Link to="/admin" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
                  {t('nav.adminPanel')}
                </Link>
              ) : null}
              <button
                type="button"
                onClick={handleSignOut}
                className="rounded-lg px-3 py-3 text-start font-medium text-clay-600 hover:bg-clay-50"
              >
                {t('nav.signOut')}
              </button>
            </>
          ) : null}

          {/* Same rule as the desktop row: signed in, the account section
              above is the control and this button would only repeat it. */}
          {isAuthenticated ? null : (
            <Button asChild block className="mt-2">
              <Link to="/login" onClick={() => setMenuOpen(false)}>
                <User className="h-4 w-4" aria-hidden="true" />
                {t('nav.login')}
              </Link>
            </Button>
          )}
        </nav>
      </div>
    </header>
  )
}
