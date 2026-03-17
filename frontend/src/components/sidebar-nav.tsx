/** Sidebar navigation — grouped sections, kbd hints, collapse support. */

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
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'
import ThemeToggle from './ThemeToggle'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ size?: number; strokeWidth?: number }>
  kbd?: string
}

interface NavGroup {
  label: string
  items: readonly NavItem[]
}

const NAV_GROUPS: readonly NavGroup[] = [
  {
    label: 'Core',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/jobs', label: 'Jobs', icon: Briefcase, kbd: '⌘J' },
      { to: '/batches', label: 'Batches', icon: Layers, kbd: '⌘B' },
    ],
  },
  {
    label: 'Data',
    items: [
      { to: '/schemas', label: 'Schemas', icon: FileText },
      { to: '/templates', label: 'Templates', icon: LayoutGrid },
    ],
  },
  {
    label: 'Quality',
    items: [
      { to: '/review-queue', label: 'Review Queue', icon: ClipboardCheck },
      { to: '/reviews', label: 'Reviews', icon: ClipboardCheck },
      { to: '/accuracy', label: 'Accuracy', icon: BarChart3 },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/pipelines', label: 'Pipelines', icon: GitBranch },
      { to: '/webhooks', label: 'Webhooks', icon: Webhook },
      { to: '/analytics', label: 'Analytics', icon: TrendingUp },
    ],
  },
] as const

const ADMIN_GROUP: NavGroup = {
  label: 'Admin',
  items: [
    { to: '/admin/policies', label: 'Policies', icon: Shield },
    { to: '/admin/users', label: 'Users', icon: Users },
  ],
} as const

/** All groups including admin — exported for command palette reuse. */
export const ALL_NAV_GROUPS: readonly NavGroup[] = [...NAV_GROUPS, ADMIN_GROUP]

interface SidebarContentProps {
  onNavigate?: () => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}

/** Sidebar content — used by both desktop sidebar and mobile Sheet. */
export function SidebarContent({ onNavigate, collapsed = false, onToggleCollapse }: SidebarContentProps) {
  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sidebar-border px-3 py-3">
          {!collapsed && (
            <div>
              <span className="text-sm font-semibold text-sidebar-foreground">Amanuo</span>
              <p className="text-[11px] text-muted-foreground">OCR Platform</p>
            </div>
          )}
          {onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
            </button>
          )}
        </div>

        {/* Nav groups */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
          {NAV_GROUPS.map((group) => (
            <NavSection key={group.label} group={group} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
          <NavSection group={ADMIN_GROUP} collapsed={collapsed} onNavigate={onNavigate} />
        </nav>

        {/* Footer: settings + theme */}
        <div className="border-t border-sidebar-border px-2 py-2 space-y-0.5">
          <NavLink
            item={{ to: '/settings', label: 'Settings', icon: Settings }}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
          <div className={collapsed ? 'flex justify-center' : 'px-1'}>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

function NavSection({ group, collapsed, onNavigate }: { group: NavGroup; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <div>
      {!collapsed && (
        <p className="px-3 mb-1 text-[11px] font-medium uppercase tracking-[0.05em] text-muted-foreground">
          {group.label}
        </p>
      )}
      <div className="space-y-0.5">
        {group.items.map((item) => (
          <NavLink key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  )
}

function NavLink({ item, collapsed, onNavigate }: { item: NavItem; collapsed: boolean; onNavigate?: () => void }) {
  const { to, label, icon: Icon, kbd } = item

  const linkContent = (
    <Link
      to={to}
      onClick={onNavigate}
      className="flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] text-muted-foreground hover:bg-accent hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      activeProps={{
        className: 'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] bg-accent text-foreground font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      }}
      activeOptions={to === '/' ? { exact: true } : undefined}
    >
      <Icon size={16} strokeWidth={1.5} />
      {!collapsed && <span className="flex-1">{label}</span>}
      {!collapsed && kbd && (
        <kbd className="text-[11px] font-mono text-muted-foreground/50">{kbd}</kbd>
      )}
    </Link>
  )

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          {label}
        </TooltipContent>
      </Tooltip>
    )
  }

  return linkContent
}
