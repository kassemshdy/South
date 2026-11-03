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
  Handshake,
  Inbox,
  MapPin,
  Megaphone,
  MessageSquareQuote,
  Image as ImageIcon,
  LayoutList,
  Menu as MenuIcon,
  Newspaper,
  PhoneCall,
  ShoppingBag,
  ShieldCheck,
  Sparkles,
  Store,
  TrendingUp,
  UserRound,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

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
      { to: '/admin/talent', labelKey: 'admin.navTalent', icon: UserRound },
      { to: '/admin/applications', labelKey: 'admin.navApplications', icon: Inbox },
      { to: '/admin/testimonials', labelKey: 'admin.navTestimonials', icon: MessageSquareQuote },
      { to: '/admin/stories', labelKey: 'admin.navStories', icon: Aperture },
    ],
  },
  {
    labelKey: 'adminNav.groupOrdersJobs',
    icon: ShoppingBag,
    items: [
      { to: '/admin/orders', labelKey: 'admin.navOrders', icon: ShoppingBag },
      { to: '/admin/job-openings', labelKey: 'admin.navJobOpenings', icon: Briefcase },
      {
        to: '/admin/employer-requests',
        labelKey: 'adminCandidate.requestsTitle',
        icon: BriefcaseBusiness,
        needs: 'employerRequests',
      },
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
      { to: '/admin/reels', labelKey: 'admin.navReels', icon: Clapperboard, needs: 'content' },
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
      { to: '/admin/users', labelKey: 'admin.navUsers', icon: Users },
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
          'flex items-center gap-2 rounded-xl px-3 py-2 font-semibold transition-colors',
          nested ? 'text-sm' : '',
          isActive ? 'bg-brand-800 text-white' : 'text-ink-700 hover:bg-sand-100',
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      {t(item.labelKey)}
    </NavLink>
  )
}

export function AdminLayout() {
  const t = useT()
  const { user } = useAuth()
  const { pathname } = useLocation()
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
    <div className="container-page py-8 print:block print:py-0 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-8">
      <div className="mb-6 print:hidden lg:sticky lg:top-24 lg:mb-0">
        {/* On a phone the menu folds behind one button naming the current
            page; from lg up it is always open, as a sidebar on the start side. */}
        <button
          type="button"
          onClick={() => setMobileOpen((value) => !value)}
          aria-expanded={mobileOpen}
          className="flex w-full items-center justify-between gap-2 rounded-2xl bg-white px-4 py-3 font-semibold text-ink-900 shadow-sm ring-1 ring-ink-100 lg:hidden"
        >
          <span className="flex items-center gap-2">
            <CurrentIcon className="h-4 w-4" aria-hidden="true" />
            {current ? t(current.labelKey) : t('admin.navAria')}
          </span>
          <ChevronDown
            className={cn('h-5 w-5 transition-transform', mobileOpen && 'rotate-180')}
            aria-hidden="true"
          />
        </button>
        <nav
          className={cn(
            'mt-2 max-h-[calc(100dvh-8rem)] space-y-1 overflow-y-auto rounded-2xl bg-white p-3 shadow-sm ring-1 ring-ink-100 lg:mt-0 lg:block',
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
                    'flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 font-semibold transition-colors hover:bg-sand-100',
                    group === currentGroup ? 'text-brand-800' : 'text-ink-700',
                  )}
                >
                  <span className="flex items-center gap-2">
                    <GroupIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {t(group.labelKey)}
                  </span>
                  <ChevronDown
                    className={cn('h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')}
                    aria-hidden="true"
                  />
                </button>
                {expanded ? (
                  <div id={id} className="ms-4 mt-1 space-y-0.5 border-s border-ink-100 ps-2">
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
      </div>

      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}
