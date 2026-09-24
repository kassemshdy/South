import {
  BarChart3,
  Bug,
  FolderTree,
  Inbox,
  MapPin,
  MessageSquareQuote,
  Newspaper,
  Sparkles,
  Store,
  UserRound,
  Users,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { useSeo } from '@/hooks/useSeo'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'

const NAV: { to: string; labelKey: TranslationKey; icon: typeof BarChart3; end: boolean }[] = [
  { to: '/admin', labelKey: 'admin.navDashboard', icon: BarChart3, end: true },
  { to: '/admin/businesses', labelKey: 'admin.navBusinesses', icon: Store, end: false },
  { to: '/admin/talent', labelKey: 'admin.navTalent', icon: UserRound, end: false },
  { to: '/admin/categories', labelKey: 'admin.navCategories', icon: FolderTree, end: false },
  { to: '/admin/talent-skills', labelKey: 'admin.navTalentSkills', icon: Sparkles, end: false },
  { to: '/admin/locations', labelKey: 'admin.navLocations', icon: MapPin, end: false },
  { to: '/admin/users', labelKey: 'admin.navUsers', icon: Users, end: false },
  { to: '/admin/applications', labelKey: 'admin.navApplications', icon: Inbox, end: false },
  {
    to: '/admin/testimonials',
    labelKey: 'admin.navTestimonials',
    icon: MessageSquareQuote,
    end: false,
  },
  { to: '/admin/articles', labelKey: 'admin.navArticles', icon: Newspaper, end: false },
  { to: '/admin/feedback', labelKey: 'admin.navFeedback', icon: Bug, end: false },
]

export function AdminLayout() {
  const t = useT()
  useSeo({ title: t('admin.seoTitle'), noIndex: true })

  return (
    <div className="container-page py-8">
      <nav className="mb-8 flex flex-wrap gap-1.5" aria-label={t('admin.navAria')}>
        {NAV.map(({ to, labelKey, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex shrink-0 items-center gap-2 rounded-full px-4 py-2.5 font-semibold transition-colors',
                isActive
                  ? 'bg-brand-800 text-white ring-1 ring-brand-900'
                  : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
              )
            }
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
