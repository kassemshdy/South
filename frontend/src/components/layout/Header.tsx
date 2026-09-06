import { LayoutDashboard, LogOut, Menu, Plus, Search, Shield, Store, User, UserCog, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { useT } from '@/i18n'
import { cn } from '@/utils/cn'

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

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-sand-50/95 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2.5 font-display text-lg font-bold text-ink-900">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-clay-500 text-white">
            <Store className="h-5 w-5" aria-hidden="true" />
          </span>
          {t('app.name')}
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label={t('nav.mainAria')}>
          <Link
            to="/businesses"
            className="rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900"
          >
            {t('nav.directory')}
          </Link>
          <Link
            to="/products"
            className="rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900"
          >
            {t('nav.products')}
          </Link>
          <Link
            to="/talent"
            className="rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100 hover:text-ink-900"
          >
            {t('nav.talent')}
          </Link>

          {isAdmin ? (
            <Link
              to="/admin"
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100"
            >
              <Shield className="h-4 w-4" aria-hidden="true" />
              {t('nav.adminPanel')}
            </Link>
          ) : null}

          {isAuthenticated ? (
            <>
              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100"
              >
                <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
                {t('nav.myBusinesses')}
              </Link>
              <Link
                to="/dashboard/account"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-[15px] font-medium text-ink-700 transition-colors hover:bg-sand-100"
              >
                <UserCog className="h-4 w-4" aria-hidden="true" />
                {t('nav.account')}
              </Link>
              <Button variant="ghost" size="sm" onClick={handleSignOut}>
                <LogOut className="h-4 w-4" aria-hidden="true" />
                {t('nav.signOutShort')}
              </Button>
            </>
          ) : (
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">
                <User className="h-4 w-4" aria-hidden="true" />
                {t('nav.login')}
              </Link>
            </Button>
          )}

          <Button asChild size="sm" className="ms-2">
            <Link to={addBusinessTarget}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('nav.addBusiness')}
            </Link>
          </Button>
        </nav>

        <div className="flex items-center gap-1 md:hidden">
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
          {isAdmin ? (
            <Link to="/admin" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
              {t('nav.adminPanel')}
            </Link>
          ) : null}
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
                {t('nav.myBusinesses')}
              </Link>
              <Link to="/dashboard/account" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 font-medium hover:bg-sand-100">
                {t('nav.account')}
              </Link>
              <p className="px-3 pt-2 text-xs text-ink-500">
                <span className="ltr-nums inline-block">{user?.phone_number ?? user?.email}</span>
              </p>
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
