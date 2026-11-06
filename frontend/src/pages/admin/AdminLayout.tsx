import {
  BarChart3,
  Briefcase,
  BriefcaseBusiness,
  ChevronDown,
  Bug,
  Aperture,
  Clapperboard,
  Download,
  FileText,
  FolderTree,
  GalleryHorizontal,
  GraduationCap,
  Home,
  Handshake,
  KeyRound,
  Inbox,
  MapPin,
  Megaphone,
  MessageSquareQuote,
  Image as ImageIcon,
  LayoutList,
  LogOut,
  Menu as MenuIcon,
  Newspaper,
  PackageX,
  PhoneCall,
  ShoppingBag,
  ShieldCheck,
  Sparkles,
  Store,
  TrendingUp,
  UserRound,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { LocaleToggle } from '@/components/layout/LocaleToggle'
import { staffCan, type StaffAction } from '@/features/admin/staffAccess'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'

type NavItem = {
  to: string
  labelKey: TranslationKey
  icon: typeof BarChart3
  end?: boolean
  /** Shown only to staff who may use it; the API refuses the rest anyway. */
  needs?: StaffAction
}

/**
 * The sections, grouped into menus (the owners' request, 3 Nov 2026): one
 * flat list of thirty links had become too long to scan. A group opens on
 * its own when it holds the current page.
 */
const GROUPS: { labelKey: TranslationKey; icon: typeof BarChart3; items: NavItem[] }[] = [
  {
    labelKey: 'adminNav.groupListings',
    icon: Store,
    items: [
      { to: '/admin/businesses', labelKey: 'admin.navBusinesses', icon: Store },
      // Beside the shops: a reviewer moves between a shop and its owner's
      // account all the time (the owners' request, 3 Nov 2026).
      { to: '/admin/users', labelKey: 'admin.navUsers', icon: Users },
      { to: '/admin/talent', labelKey: 'admin.navTalent', icon: UserRound },
      { to: '/admin/applications', labelKey: 'admin.navApplications', icon: Inbox },
      { to: '/admin/shops-without-products', labelKey: 'adminShops.noProductsNav', icon: PackageX },
      { to: '/admin/testimonials', labelKey: 'admin.navTestimonials', icon: MessageSquareQuote },
      { to: '/admin/stories', labelKey: 'admin.navStories', icon: Aperture },
    ],
  },
  {
    labelKey: 'adminNav.groupOrdersJobs',
    icon: ShoppingBag,
    items: [
      { to: '/admin/orders', labelKey: 'admin.navOrders', icon: ShoppingBag },
      { to: '/admin/service-requests', labelKey: 'openRequest.nav', icon: Wrench },
      { to: '/admin/job-openings', labelKey: 'admin.navJobOpenings', icon: Briefcase },
      {
        to: '/admin/employer-requests',
        labelKey: 'adminCandidate.requestsTitle',
        icon: BriefcaseBusiness,
        needs: 'employerRequests',
      },
      { to: '/admin/shopify', labelKey: 'admin.navShopify', icon: Store },
      { to: '/admin/api-partners', labelKey: 'admin.navApiPartners', icon: KeyRound, needs: 'manage' },
    ],
  },
  {
    labelKey: 'adminNav.groupContent',
    icon: Newspaper,
    items: [
      { to: '/admin/articles', labelKey: 'admin.navArticles', icon: Newspaper },
      { to: '/admin/activities', labelKey: 'admin.navActivities', icon: Megaphone },
      { to: '/admin/carousel', labelKey: 'adminCarousel.nav', icon: GalleryHorizontal },
      { to: '/admin/workshops', labelKey: 'admin.navWorkshops', icon: GraduationCap },
      { to: '/admin/partners', labelKey: 'admin.navPartners', icon: Handshake },
      { to: '/admin/reels', labelKey: 'admin.navReels', icon: Clapperboard, needs: 'reels' },
      { to: '/admin/pages', labelKey: 'admin.navPages', icon: FileText },
    ],
  },
  {
    labelKey: 'adminNav.groupSite',
    icon: LayoutList,
    items: [
      { to: '/admin/home-layout', labelKey: 'admin.navHomeLayout', icon: LayoutList, needs: 'content' },
      { to: '/admin/menu', labelKey: 'admin.navMenu', icon: MenuIcon, needs: 'content' },
      { to: '/admin/page-covers', labelKey: 'admin.navPageCovers', icon: ImageIcon },
      { to: '/admin/site-settings', labelKey: 'nav.contact', icon: PhoneCall, needs: 'manage' },
    ],
  },
  {
    labelKey: 'adminNav.groupTaxonomy',
    icon: FolderTree,
    items: [
      { to: '/admin/categories', labelKey: 'admin.navCategories', icon: FolderTree },
      { to: '/admin/talent-skills', labelKey: 'admin.navTalentSkills', icon: Sparkles },
      { to: '/admin/locations', labelKey: 'admin.navLocations', icon: MapPin },
    ],
  },
  {
    labelKey: 'adminNav.groupAccounts',
    icon: Users,
    items: [
      { to: '/admin/staff', labelKey: 'admin.navStaff', icon: ShieldCheck, needs: 'manage' },
    ],
  },
  {
    labelKey: 'adminNav.groupReports',
    icon: TrendingUp,
    items: [
      { to: '/admin/growth', labelKey: 'growth.nav', icon: TrendingUp },
      { to: '/admin/feedback', labelKey: 'admin.navFeedback', icon: Bug },
      { to: '/admin/export', labelKey: 'admin.navExport', icon: Download, needs: 'manage' },
    ],
  },
]

const DASHBOARD: NavItem = { to: '/admin', labelKey: 'admin.navDashboard', icon: BarChart3, end: true }

function isCurrent(item: NavItem, pathname: string): boolean {
  return item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`)
}

function NavEntry({ item, nested, onNavigate }: { item: NavItem; nested?: boolean; onNavigate: () => void }) {
  const t = useT()
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2 rounded-xl px-3 py-2 font-semibold transition-colors lg:gap-3 lg:px-4 lg:py-3.5',
          nested ? 'text-sm lg:text-base' : 'lg:text-lg',
          isActive ? 'bg-brand-800 text-white' : 'text-ink-700 hover:bg-sand-100',
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0 lg:h-5 lg:w-5" aria-hidden="true" />
      {t(item.labelKey)}
    </NavLink>
  )
}

export function AdminLayout() {
  const t = useT()
  const { user, signOut } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const account = user?.email ?? user?.phone_number
  const handleSignOut = () => {
    signOut()
    navigate('/')
  }
  useSeo({ title: t('admin.seoTitle'), noIndex: true })

  const groups = GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.needs || staffCan(user?.staff_role, item.needs)),
  })).filter((group) => group.items.length > 0)
  const currentGroup = groups.find((group) => group.items.some((item) => isCurrent(item, pathname)))
  const current =
    currentGroup?.items.find((item) => isCurrent(item, pathname)) ??
    (isCurrent(DASHBOARD, pathname) ? DASHBOARD : null)

  const [open, setOpen] = useState<Set<TranslationKey>>(
    () => new Set(currentGroup ? [currentGroup.labelKey] : []),
  )
  // A page reached from a link elsewhere opens its own group too.
  useEffect(() => {
    if (!currentGroup) return
    setOpen((previous) =>
      previous.has(currentGroup.labelKey) ? previous : new Set(previous).add(currentGroup.labelKey),
    )
  }, [currentGroup])
  const [mobileOpen, setMobileOpen] = useState(false)
  const toggle = (key: TranslationKey) =>
    setOpen((previous) => {
      const next = new Set(previous)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  const CurrentIcon = current?.icon ?? MenuIcon

  return (
    <div className="min-h-screen bg-sand-50 lg:ps-72 xl:ps-80 print:bg-white print:ps-0">
      {/* An admin panel of its own (the owner's request, 4 Nov 2026): the
          website's header, section menu and footer are not drawn on /admin
          (AppLayout), and the menu is a sidebar fixed to the start side for
          the screen's full height, with the way back to the site, the
          language and signing out at its foot. On a phone it is a slim bar
          whose button unfolds the same menu. */}
      <aside className="sticky top-0 z-30 print:hidden lg:fixed lg:inset-y-0 lg:start-0 lg:flex lg:w-72 lg:flex-col lg:border-e lg:border-ink-100 lg:bg-white xl:w-80">
        <div className="flex h-16 items-center justify-between gap-3 border-b border-ink-100 bg-white px-4 lg:h-20 lg:px-5">
          <Link to="/admin" className="flex min-w-0 items-center gap-3">
            <img
              src="/janoubona-logo.webp"
              alt={t('app.name')}
              width={450}
              height={191}
              className="h-9 w-auto shrink-0 lg:h-10"
            />
            <span className="truncate font-bold text-ink-900 lg:text-lg">{t('nav.adminPanel')}</span>
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((value) => !value)}
            aria-expanded={mobileOpen}
            aria-controls="admin-nav"
            className="flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-ink-900 ring-1 ring-ink-100 lg:hidden"
          >
            <CurrentIcon className="h-4 w-4" aria-hidden="true" />
            <span className="max-w-[9rem] truncate">
              {current ? t(current.labelKey) : t('admin.navAria')}
            </span>
            {mobileOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <MenuIcon className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
        <nav
          id="admin-nav"
          className={cn(
            'max-h-[calc(100dvh-8rem)] space-y-1 overflow-y-auto border-b border-ink-100 bg-white p-3 lg:block lg:max-h-none lg:flex-1 lg:space-y-2 lg:border-0 lg:p-4',
            mobileOpen ? 'block' : 'hidden',
          )}
          aria-label={t('admin.navAria')}
        >
          <NavEntry item={DASHBOARD} onNavigate={() => setMobileOpen(false)} />
          {groups.map((group) => {
            const expanded = open.has(group.labelKey)
            const GroupIcon = group.icon
            const id = `admin-nav-${group.labelKey.replace(/\W/g, '-')}`
            return (
              <div key={group.labelKey}>
                <button
                  type="button"
                  onClick={() => toggle(group.labelKey)}
                  aria-expanded={expanded}
                  aria-controls={id}
                  className={cn(
                    'flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 font-semibold transition-colors hover:bg-sand-100 lg:px-4 lg:py-3.5 lg:text-lg',
                    group === currentGroup ? 'text-brand-800' : 'text-ink-700',
                  )}
                >
                  <span className="flex items-center gap-2 lg:gap-3">
                    <GroupIcon className="h-4 w-4 shrink-0 lg:h-5 lg:w-5" aria-hidden="true" />
                    {t(group.labelKey)}
                  </span>
                  <ChevronDown
                    className={cn('h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')}
                    aria-hidden="true"
                  />
                </button>
                {expanded ? (
                  <div id={id} className="ms-4 mt-1 space-y-0.5 border-s border-ink-100 ps-2 lg:space-y-1">
                    {group.items.map((item) => (
                      <NavEntry
                        key={item.to}
                        item={item}
                        nested
                        onNavigate={() => setMobileOpen(false)}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            )
          })}
        </nav>
        <div
          className={cn(
            'flex-wrap items-center gap-2 border-b border-ink-100 bg-white p-3 lg:flex lg:border-b-0 lg:border-t lg:p-4',
            mobileOpen ? 'flex' : 'hidden',
          )}
        >
          {account ? (
            <p className="w-full truncate text-xs text-ink-500" dir="ltr">
              {account}
            </p>
          ) : null}
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-ink-700 hover:bg-sand-100"
          >
            <Home className="h-4 w-4" aria-hidden="true" />
            {t('nav.home')}
          </Link>
          <LocaleToggle />
          <button
            type="button"
            onClick={handleSignOut}
            className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-clay-700 hover:bg-clay-50"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            {t('nav.signOut')}
          </button>
        </div>
      </aside>

      <div className="min-w-0 px-4 py-8 sm:px-6 lg:px-8 print:p-0">
        <Outlet />
      </div>
    </div>
  )
}
