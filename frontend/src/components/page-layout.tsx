/** Main page layout with collapsible sidebar, header breadcrumb, and content area. */

import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '#/components/ui/sheet'
import { SidebarContent } from './sidebar-nav'

const COLLAPSED_KEY = 'sidebar_collapsed'

interface PageLayoutProps {
  title: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
}

export function PageLayout({ title, description, actions, children }: PageLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(COLLAPSED_KEY) === 'true'
  })

  useEffect(() => {
    window.localStorage.setItem(COLLAPSED_KEY, String(collapsed))
  }, [collapsed])

  const sidebarWidth = collapsed ? 'w-14' : 'w-56'
  const mainOffset = collapsed ? 'md:ml-14' : 'md:ml-56'

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className={`hidden md:flex fixed left-0 top-0 h-full ${sidebarWidth} border-r border-sidebar-border bg-sidebar-background flex-col z-20 transition-[width] duration-200`}>
        <SidebarContent collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)} />
      </aside>

      {/* Mobile sidebar (Sheet) */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-56 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className={`${mainOffset} flex-1 flex flex-col min-h-screen overflow-auto transition-[margin] duration-200`}>
        {/* Header */}
        <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-sm px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="md:hidden inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer"
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0">
              <h1 className="text-base font-semibold text-foreground truncate">{title}</h1>
              {description && (
                <p className="text-[12px] text-muted-foreground truncate">{description}</p>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex items-center gap-2 shrink-0">{actions}</div>
          )}
        </header>

        {/* Content */}
        <main className="flex-1 px-6 py-5">{children}</main>
      </div>
    </div>
  )
}
