/** Main page layout with sidebar and content area. */

import { SidebarNav } from './sidebar-nav'

interface PageLayoutProps {
  title: string
  actions?: React.ReactNode
  children: React.ReactNode
}

export function PageLayout({ title, actions, children }: PageLayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      <SidebarNav />
      <div className="ml-56 flex-1 flex flex-col min-h-screen overflow-auto">
        <header className="sticky top-0 z-10 border-b border-gray-200 bg-white px-6 py-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  )
}
