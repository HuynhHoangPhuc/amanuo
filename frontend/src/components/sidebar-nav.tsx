/** Sidebar navigation with active route highlighting. */

import { Link } from '@tanstack/react-router'
import {
  LayoutDashboard,
  FileText,
  Briefcase,
  GitBranch,
  Layers,
  Webhook,
  Settings,
  LayoutGrid,
  ClipboardCheck,
  BarChart3,
  TrendingUp,
  Shield,
  Users,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/schemas', label: 'Schemas', icon: FileText },
  { to: '/templates', label: 'Templates', icon: LayoutGrid },
  { to: '/jobs', label: 'Jobs', icon: Briefcase },
  { to: '/review-queue', label: 'Review Queue', icon: ClipboardCheck },
  { to: '/reviews', label: 'Reviews', icon: ClipboardCheck },
  { to: '/pipelines', label: 'Pipelines', icon: GitBranch },
  { to: '/batches', label: 'Batches', icon: Layers },
  { to: '/accuracy', label: 'Accuracy', icon: BarChart3 },
  { to: '/analytics', label: 'Analytics', icon: TrendingUp },
  { to: '/webhooks', label: 'Webhooks', icon: Webhook },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const ADMIN_ITEMS = [
  { to: '/admin/policies', label: 'Policies', icon: Shield },
  { to: '/admin/users', label: 'Users', icon: Users },
]

export function SidebarNav() {
  return (
    <aside className="fixed left-0 top-0 h-full w-56 border-r border-gray-200 bg-white flex flex-col">
      <div className="px-4 py-5 border-b border-gray-100">
        <span className="text-lg font-bold text-gray-900">Amanuo</span>
        <p className="text-xs text-gray-500 mt-0.5">OCR Platform</p>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
            activeProps={{ className: 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm bg-blue-50 text-blue-700 font-medium' }}
            activeOptions={to === '/' ? { exact: true } : undefined}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}

        {/* Admin section */}
        <div className="pt-4 mt-4 border-t border-gray-100">
          <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wide">Admin</p>
          {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
              activeProps={{ className: 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm bg-blue-50 text-blue-700 font-medium' }}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </aside>
  )
}
