import { BarChart3, FolderTree, MapPin, Store, Users } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { useSeo } from '@/hooks/useSeo'
import { cn } from '@/utils/cn'

const NAV = [
  { to: '/admin', label: 'لوحة التحكم', icon: BarChart3, end: true },
  { to: '/admin/businesses', label: 'النشاطات', icon: Store, end: false },
  { to: '/admin/categories', label: 'التصنيفات', icon: FolderTree, end: false },
  { to: '/admin/locations', label: 'المواقع', icon: MapPin, end: false },
  { to: '/admin/users', label: 'المستخدمون', icon: Users, end: false },
]

export function AdminLayout() {
  useSeo({ title: 'لوحة الإدارة | دليل الجنوب', noIndex: true })

  return (
    <div className="container-page py-8">
      <nav className="mb-8 flex gap-1.5 overflow-x-auto pb-1" aria-label="أقسام لوحة الإدارة">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 font-semibold transition-colors',
                isActive ? 'bg-clay-500 text-white' : 'bg-white text-ink-700 ring-1 ring-ink-100 hover:bg-sand-100',
              )
            }
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
