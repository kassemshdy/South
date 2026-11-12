import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import {
  ArrowLeft,
  ChevronDown,
  Heart,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  ShoppingBag,
  Shield,
  User,
  UserCog,
  X,
} from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useSiteSections } from '@/components/layout/navigation'
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
 * "more" menu — to keep the row short; that was overruled, because a
 * heading somebody has to find is not a heading.
 *
 * The language switch is not in the header at all: the owners asked for it in
 * the footer, beside the social accounts, since it is touched once and a
 * button wide enough to carry «English» costs a heading's worth of width.
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
  'whitespace-nowrap rounded-lg px-1.5 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900 2xl:px-3'

const MENU_ITEM =
  'flex cursor-pointer select-none items-center gap-2.5 rounded-lg px-3 py-2.5 text-[15px] text-ink-700 outline-none data-[highlighted]:bg-sand-100 data-[highlighted]:text-ink-900'

/**
 * Whether the full row of headings fits beside the logo.
 *
 * Administrators choose which headings the menu shows (`/admin/menu`), so the
 * row's width is not known when the page is written: six headings fit at
 * 1280px, eleven do not, and an overflowing row pushed the whole page sideways
 * -- an RTL page scrolled to a blank strip with the logo cut off. So the row
 * is measured rather than assumed: below `xl` the drawer is used as before,
 * and from `xl` up the row is shown only while it actually fits; otherwise
 * the same drawer takes over. Measured again whenever the bar or the row
 * changes size (a resize, the web font arriving, a heading renamed).
 */
function useRowFits() {
  const barRef = useRef<HTMLDivElement>(null)
  const logoRef = useRef<HTMLAnchorElement>(null)
  const navRef = useRef<HTMLElement>(null)
  const [fits, setFits] = useState(true)

  useLayoutEffect(() => {
    const bar = barRef.current
    const logo = logoRef.current
    const nav = navRef.current
    if (!bar || !logo || !nav) return
    const measure = () => {
      // Below `xl` the row is display:none and measures 0: it "fits", and
      // the `xl:` classes it would affect do not apply there anyway.
      const style = getComputedStyle(bar)
      const available =
        bar.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
      const gap = parseFloat(style.columnGap) || 0
      setFits(nav.scrollWidth + logo.offsetWidth + gap <= available)
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(bar)
    observer.observe(nav)
    return () => observer.disconnect()
  }, [])

  return { barRef, logoRef, navRef, fits }
}

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

/** A menu row for the cart or saved items, absent while empty like the icons. */
function MenuCountLink({
  to,
  icon: Icon,
  label,
  count,
  onClick,
}: {
  to: string
  icon: typeof Heart
  label: string
  count: number
  onClick: () => void
}) {
  if (count === 0) return null
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center gap-2.5 rounded-lg px-3 py-3 font-medium hover:bg-sand-100"
    >
      <Icon className="h-5 w-5 text-ink-500" aria-hidden="true" />
      {label}
      <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-clay-500 px-1.5 text-xs font-bold text-white ltr-nums">
        {count}
      </span>
    </Link>
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

export function Header() {
  const { isAuthenticated, isAdmin, user, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const { count: cartCount } = useCart()
  const { count: favouritesCount } = useFavourites()
  const navigate = useNavigate()
  const t = useT()
  const sections = useSiteSections()

  const { barRef, logoRef, navRef, fits } = useRowFits()

  const handleSignOut = () => {
    signOut()
    setMenuOpen(false)
    navigate('/')
  }

  const account = user?.phone_number ?? user?.email

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-sand-50/95 backdrop-blur">
      {/* A way in for whoever has something to offer, above everything else.
          It used to sit halfway down the homepage, so a seller had to scroll
          past the buyer's half of the site to find it -- while a buyer had
          the whole bar of sections. The owners asked for it at the top, in
          their own words; a strip of its own rather than a seventh item in
          a row that already fills 1280px. It opens the shop application
          itself (the owners' request, 2 Nov 2026), which carries its own
          notice and steps; /offer keeps the three doors. */}
      <Link
        to="/register/business"
        className="flex h-9 items-center justify-center gap-2 bg-brand-700 px-4 text-sm font-semibold text-white transition-colors hover:bg-brand-800"
      >
        {t('nav.offer')}
        <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
      </Link>
      <div
        ref={barRef}
        className="container-page relative flex h-20 items-center justify-between gap-4 overflow-hidden"
      >
        {/* The hit area is the bar's full height and reaches a little past
            the artwork on each side. Sizing it to the image alone left a
            106x40 target in a 64px bar — the logo looked dead to anyone whose
            cursor landed above, below or just beside the glyphs, which is
            most of the time. The negative margin cancels the padding, so the
            target grows without the logo moving. `cursor-pointer` is stated
            rather than inherited from the anchor, so the whole padded area
            reads as clickable and not just the image inside it. */}
        <Link
          ref={logoRef}
          to="/"
          className="-mx-2 flex h-full shrink-0 cursor-pointer items-center px-2"
        >
          {/* The whole logo, wordmark and emblem together, rather than the
              emblem beside the name set in a UI font. The name in the logo is
              drawn lettering, so setting it again in the interface typeface
              put two versions of the same word side by side in two different
              hands. `alt` carries the name because the image *is* the name
              now; an empty alt would leave a screen reader with nothing.

              Transparent WebP, so the mark sits on the sand bar here and on
              the white footer without a beige slab behind it. 450px wide:
              three times the widest it is ever drawn (the footer), where the
              1400px original was 189 KB on every page for a 48px logo. */}
          <img
            src="/janoubona-logo.webp"
            alt={t('app.name')}
            width={450}
            height={191}
            /* The CEO asked for the bar to grow so the logo can be read: the
               lockup carries the three pillars and a sub-line under the name,
               and at 48px in a 64px bar the sub-line was strokes rather than
               letters. 80px now, with the logo at 56-64px. */
            className="h-11 w-auto max-[379px]:h-10 sm:h-14 xl:h-16"
          />
        </Link>

        {/* When it does not fit, the row stays in the page only to be
            measured: invisible (so neither seen, tabbed to nor read out) and
            out of the flow, while the drawer below takes its place. */}
        <nav
          ref={navRef}
          className={cn(
            'hidden items-center gap-1 xl:flex',
            !fits && 'pointer-events-none invisible absolute end-0 top-0',
          )}
          aria-label={t('nav.mainAria')}
          aria-hidden={fits ? undefined : true}
        >
          {sections.map((section) => (
            <Link key={section.href} to={section.href} className={NAV_LINK}>
              {section.label}
            </Link>
          ))}

          {/* Search, as an icon: it opens goods and products, where the search
              box is. It used to open the business directory, which the site no
              longer links (see `navigation.ts`). */}
          <Button asChild variant="ghost" size="icon" aria-label={t('nav.searchAria')}>
            <Link to="/products">
              <Search className="h-5 w-5" aria-hidden="true" />
            </Link>
          </Button>

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

        <div className={cn('flex shrink-0 items-center gap-1', fits && 'xl:hidden')}>
          {/* On phones and tablets the cart and saved items are in the menu
              (the owners' request, 12 Nov 2026), leaving the bar to the logo,
              the account button and the menu button. */}
          <div className="contents max-xl:hidden">
            <CartLink />
            <FavouritesLink />
          </div>
          {/* The way in, or the way to one's own area, stays in the bar beside
              search and the menu button: once the headings stopped fitting
              beside the logo, the account controls above went with them (the
              owners' request, 4 Nov 2026). A labelled button, not a bare
              person icon -- visitors did not read the icon as a way in, and
              a signed-in owner had no way to their area but the menu (5 Nov
              2026). On phones the icon inside it goes and the button is smaller,
              and there is no search button (the owners' request, 12 Nov
              2026: «السلع والمنتجات» in the menu is the way in), so the
              menu button always fits. */}
          <Button
            asChild
            size="sm"
            className="me-1 shrink-0 whitespace-nowrap max-sm:min-h-8 max-sm:px-2.5 max-sm:text-xs"
          >
            {isAuthenticated ? (
              <Link to={isAdmin ? '/admin' : '/dashboard'}>
                {isAdmin ? (
                  <Shield className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                ) : (
                  <LayoutDashboard className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                )}
                {isAdmin ? t('nav.adminPanel') : t('nav.myBusinesses')}
              </Link>
            ) : (
              <Link to="/login">
                <User className="h-4 w-4 max-[419px]:hidden" aria-hidden="true" />
                {t('nav.login')}
              </Link>
            )}
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

      {/* On a desktop the headings are never hidden behind the menu button
          (the owners' urgent request, 3 Nov 2026): when they do not fit
          beside the logo they take one line of their own under it, never two
          (the owners' request). Phones and tablets keep the drawer. */}
      {!fits ? (
        <nav
          className="hidden border-t border-ink-100 xl:block"
          aria-label={t('nav.mainAria')}
        >
          <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-center gap-x-1 overflow-x-auto px-4 py-1.5">
            {sections.map((section) => (
              <Link
                key={section.href}
                to={section.href}
                className="whitespace-nowrap rounded-lg px-2.5 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900"
              >
                {section.label}
              </Link>
            ))}
          </div>
        </nav>
      ) : null}

      <div
        id="mobile-menu"
        className={cn(
          'border-t border-ink-100 bg-white',
          fits && 'xl:hidden',
          menuOpen ? 'block' : 'hidden',
        )}
      >
        <nav className="container-page flex flex-col gap-1 py-3" aria-label={t('nav.mobileAria')}>
          <MenuCountLink
            to="/favourites"
            icon={Heart}
            label={t('favourites.link')}
            count={favouritesCount}
            onClick={() => setMenuOpen(false)}
          />
          <MenuCountLink
            to="/cart"
            icon={ShoppingBag}
            label={t('cart.link')}
            count={cartCount}
            onClick={() => setMenuOpen(false)}
          />
          {sections.map((section) => (
            <Link
              key={section.href}
              to={section.href}
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100"
            >
              {section.label}
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
