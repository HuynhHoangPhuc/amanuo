/** Sidebar navigation — enterprise-style grouped sections with workspace header. */

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
  ScanLine,
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
        {/* Workspace header */}
        <div className="flex items-center gap-2.5 border-b border-sidebar-border px-3 py-3.5">
          {!collapsed && (
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ScanLine size={16} strokeWidth={2} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-sidebar-foreground truncate">Amanuo</p>
                <p className="text-[11px] text-sidebar-muted-foreground leading-none">OCR Platform</p>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="flex h-8 w-8 mx-auto shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ScanLine size={16} strokeWidth={2} />
            </div>
          )}
        </div>

        {/* Nav groups */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-5">
          {NAV_GROUPS.map((group) => (
            <NavSection key={group.label} group={group} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
          <NavSection group={ADMIN_GROUP} collapsed={collapsed} onNavigate={onNavigate} />
        </nav>

        {/* Footer: settings + theme + collapse */}
        <div className="border-t border-sidebar-border px-2 py-2.5 space-y-0.5">
          <NavLink
            item={{ to: '/settings', label: 'Settings', icon: Settings }}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
          <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between px-1'}`}>
            <ThemeToggle />
            {onToggleCollapse && (
              <button
                type="button"
                onClick={onToggleCollapse}
                className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
              </button>
            )}
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
        <p className="px-3 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-muted-foreground">
          {group.label}
        </p>
      )}
      {collapsed && <div className="mx-3 mb-1.5 border-t border-sidebar-border" />}
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
      className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium text-sidebar-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      activeProps={{
        className: 'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium bg-sidebar-accent text-sidebar-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      }}
      activeOptions={to === '/' ? { exact: true } : undefined}
    >
      <Icon size={16} strokeWidth={1.75} />
      {!collapsed && <span className="flex-1 truncate">{label}</span>}
      {!collapsed && kbd && (
        <kbd className="text-[10px] font-mono text-sidebar-muted-foreground/50 bg-sidebar-accent/50 px-1.5 py-0.5 rounded">{kbd}</kbd>
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
