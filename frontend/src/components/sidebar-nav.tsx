/** Sidebar navigation with active route highlighting — theme-aware. */

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
] as const

const ADMIN_ITEMS = [
  { to: '/admin/policies', label: 'Policies', icon: Shield },
  { to: '/admin/users', label: 'Users', icon: Users },
] as const

interface SidebarContentProps {
  onNavigate?: () => void
}

/** Extracted nav content — used by both desktop sidebar and mobile Sheet. */
export function SidebarContent({ onNavigate }: SidebarContentProps) {
  return (
    <>
      <div className="px-4 py-5 border-b border-sidebar-border">
        <span className="text-lg font-bold text-sidebar-foreground">Amanuo</span>
        <p className="text-xs text-muted-foreground mt-0.5">OCR Platform</p>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            onClick={onNavigate}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            activeProps={{ className: 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm bg-primary/10 text-primary font-medium' }}
            activeOptions={to === '/' ? { exact: true } : undefined}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}

        {/* Admin section */}
        <div className="pt-4 mt-4 border-t border-sidebar-border/50">
          <p className="px-3 pb-1 text-xs font-semibold text-muted-foreground/70 uppercase tracking-wide">Admin</p>
          {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              onClick={onNavigate}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              activeProps={{ className: 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm bg-primary/10 text-primary font-medium' }}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  )
}

