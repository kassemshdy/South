import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Search,
  ShoppingBag,
  Shield,
  Store,
  User,
  UserCog,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { LocaleToggle } from '@/components/layout/LocaleToggle'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { useCart } from '@/features/cart/CartContext'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

/**
 * The header holds the same number of things whether or not anybody is signed
 * in.
 *
 * It used to grow: signing in appended `nav.myBusinesses`, `nav.account` and
 * a sign-out button, plus `nav.adminPanel` for an admin, so the people who use
 * the site most got the most crowded bar — eight items and a call to action
 * competing on one line. The public links stay three, and everything personal
 * now lives behind one account menu. The `nav.addBusiness` button keeps its
 * place whether or not anybody is signed in; only where it leads changes.
 *
 * (Key names rather than the strings themselves: `tests/test_i18n.py` scans
 * this directory for Arabic codepoints, comments included.)
 */

const NAV_LINK =
  'rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900'

const MENU_ITEM =
  'flex cursor-pointer select-none items-center gap-2.5 rounded-lg px-3 py-2.5 text-[15px] text-ink-700 outline-none data-[highlighted]:bg-sand-100 data-[highlighted]:text-ink-900'

function CartLink({ compact = false }: { compact?: boolean }) {
  const t = useT()
  const { count } = useCart()

  // Absent when empty rather than showing a zero: a permanent cart icon on a
  // directory suggests a shop, and this is only a shop once someone has put
  // something in it.
  if (count === 0) return null

  return (
    <Button asChild variant="ghost" size={compact ? 'icon' : 'sm'} aria-label={t('cart.link')}>
      <Link to="/cart" className="relative">
        <ShoppingBag className="h-5 w-5" aria-hidden="true" />
        <span className="absolute -end-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-clay-500 px-1 text-[10px] font-bold text-white ltr-nums">
          {count}
        </span>
        {compact ? null : <span className="ms-1.5">{t('cart.link')}</span>}
      </Link>
    </Button>
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

  const addBusinessTarget = isAuthenticated ? '/dashboard/businesses/new' : '/login'
  const account = user?.phone_number ?? user?.email

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-sand-50/95 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2.5 font-display text-lg font-bold text-ink-900">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white">
            <Store className="h-5 w-5" aria-hidden="true" />
          </span>
          {t('app.name')}
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label={t('nav.mainAria')}>
          <Link to="/businesses" className={NAV_LINK}>
            {t('nav.directory')}
          </Link>
          <Link to="/products" className={NAV_LINK}>
            {t('nav.products')}
          </Link>
          <Link to="/talent" className={NAV_LINK}>
            {t('nav.talent')}
          </Link>

          <LocaleToggle />

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
          ) : (
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">
                <User className="h-4 w-4" aria-hidden="true" />
                {t('nav.login')}
              </Link>
            </Button>
          )}

          <CartLink />

          <Button asChild size="sm" className="ms-2">
            <Link to={addBusinessTarget}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('nav.addBusiness')}
            </Link>
          </Button>
        </nav>

        <div className="flex items-center gap-1 md:hidden">
          <CartLink compact />
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
        className={cn('border-t border-ink-100 bg-white md:hidden', menuOpen ? 'block' : 'hidden')}
      >
        <nav className="container-page flex flex-col gap-1 py-3" aria-label={t('nav.mobileAria')}>
          <Link to="/businesses" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
            {t('nav.directory')}
          </Link>
          <Link to="/products" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
            {t('nav.products')}
          </Link>
          <Link to="/talent" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
            {t('nav.talent')}
          </Link>

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
          ) : (
            <Link to="/login" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
              {t('nav.login')}
            </Link>
          )}

          <Button asChild block className="mt-2">
            <Link to={addBusinessTarget} onClick={() => setMenuOpen(false)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('nav.addBusiness')}
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  )
}
