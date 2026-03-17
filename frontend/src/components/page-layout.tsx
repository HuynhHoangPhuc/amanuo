/** Main page layout with collapsible sidebar, slim header, and content area. */

import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '#/components/ui/sheet'
import { SidebarContent } from './sidebar-nav'

const COLLAPSED_KEY = 'sidebar_collapsed'

interface PageLayoutProps {
  title: string
  actions?: React.ReactNode
  children: React.ReactNode
}

export function PageLayout({ title, actions, children }: PageLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(COLLAPSED_KEY) === 'true'
  })

  useEffect(() => {
    window.localStorage.setItem(COLLAPSED_KEY, String(collapsed))
  }, [collapsed])

  const sidebarWidth = collapsed ? 'w-12' : 'w-52'
  const mainOffset = collapsed ? 'md:ml-12' : 'md:ml-52'

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className={`hidden md:flex fixed left-0 top-0 h-full ${sidebarWidth} border-r border-sidebar-border bg-sidebar-background flex-col z-20 transition-[width] duration-200`}>
        <SidebarContent collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)} />
      </aside>

      {/* Mobile sidebar (Sheet) */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-52 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className={`${mainOffset} flex-1 flex flex-col min-h-screen overflow-auto transition-[margin] duration-200`}>
        <header className="sticky top-0 z-10 border-b border-border bg-background px-4 py-2.5 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="md:hidden inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>
          <h1 className="text-sm font-semibold text-foreground">{title}</h1>
          <div className="ml-auto flex items-center gap-1.5">{actions}</div>
        </header>
        <main className="flex-1 px-4 py-4">{children}</main>
      </div>
    </div>
  )
}
