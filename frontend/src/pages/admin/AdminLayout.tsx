import {
  BarChart3,
  Bug,
  Aperture,
  Clapperboard,
  Download,
  FileText,
  FolderTree,
  Handshake,
  Inbox,
  MapPin,
  MessageSquareQuote,
  Image as ImageIcon,
  LayoutList,
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
import { NavLink, Outlet } from 'react-router-dom'

import { staffCan, type StaffAction } from '@/features/admin/staffAccess'
import { useAuth } from '@/features/auth/AuthContext'
import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'

const NAV: {
  to: string
  labelKey: TranslationKey
  icon: typeof BarChart3
  end: boolean
  /** Shown only to staff who may use it; the API refuses the rest anyway. */
  needs?: StaffAction
}[] = [
  { to: '/admin', labelKey: 'admin.navDashboard', icon: BarChart3, end: true },
  { to: '/admin/businesses', labelKey: 'admin.navBusinesses', icon: Store, end: false },
  { to: '/admin/talent', labelKey: 'admin.navTalent', icon: UserRound, end: false },
  { to: '/admin/categories', labelKey: 'admin.navCategories', icon: FolderTree, end: false },
  { to: '/admin/talent-skills', labelKey: 'admin.navTalentSkills', icon: Sparkles, end: false },
  { to: '/admin/locations', labelKey: 'admin.navLocations', icon: MapPin, end: false },
  { to: '/admin/users', labelKey: 'admin.navUsers', icon: Users, end: false },
  { to: '/admin/growth', labelKey: 'growth.nav', icon: TrendingUp, end: false },
  { to: '/admin/orders', labelKey: 'admin.navOrders', icon: ShoppingBag, end: false },
  { to: '/admin/applications', labelKey: 'admin.navApplications', icon: Inbox, end: false },
  { to: '/admin/partners', labelKey: 'admin.navPartners', icon: Handshake, end: false },
  { to: '/admin/stories', labelKey: 'admin.navStories', icon: Aperture, end: false },
  {
    to: '/admin/testimonials',
    labelKey: 'admin.navTestimonials',
    icon: MessageSquareQuote,
    end: false,
  },
  { to: '/admin/articles', labelKey: 'admin.navArticles', icon: Newspaper, end: false },
  { to: '/admin/pages', labelKey: 'admin.navPages', icon: FileText, end: false },
  { to: '/admin/page-covers', labelKey: 'admin.navPageCovers', icon: ImageIcon, end: false },
  { to: '/admin/home-layout', labelKey: 'admin.navHomeLayout', icon: LayoutList, end: false, needs: 'content' },
  { to: '/admin/reels', labelKey: 'admin.navReels', icon: Clapperboard, end: false, needs: 'content' },
  { to: '/admin/site-settings', labelKey: 'nav.contact', icon: PhoneCall, end: false, needs: 'manage' },
  { to: '/admin/feedback', labelKey: 'admin.navFeedback', icon: Bug, end: false },
  { to: '/admin/export', labelKey: 'admin.navExport', icon: Download, end: false, needs: 'manage' },
  { to: '/admin/staff', labelKey: 'admin.navStaff', icon: ShieldCheck, end: false, needs: 'manage' },
]

export function AdminLayout() {
  const t = useT()
  const { user } = useAuth()
  useSeo({ title: t('admin.seoTitle'), noIndex: true })

  return (
    <div className="container-page py-8 print:block print:py-0 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-8">
      {/* A sidebar on the start side from lg up -- the right in Arabic -- so
          the sections read as a list rather than two rows of pills that grow
          with every new screen. On a phone it stays one row that scrolls
          sideways: a column there would push the page itself off screen. */}
      <nav
        className="-mx-4 mb-6 flex gap-1.5 print:hidden overflow-x-auto px-4 pb-2 lg:sticky lg:top-24 lg:mx-0 lg:mb-0 lg:flex-col lg:gap-1 lg:overflow-visible lg:rounded-2xl lg:bg-white lg:p-3 lg:shadow-sm lg:ring-1 lg:ring-ink-100"
        aria-label={t('admin.navAria')}
      >
        {NAV.filter((item) => !item.needs || staffCan(user?.staff_role, item.needs)).map(({ to, labelKey, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex shrink-0 items-center gap-2 rounded-full px-4 py-2.5 font-semibold transition-colors lg:rounded-xl lg:px-3',
                isActive
                  ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                  : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100 lg:ring-0',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}
