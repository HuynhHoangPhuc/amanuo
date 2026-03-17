/** Root route: wires up QueryClient, ToastProvider, and WebSocket event stream. */

import { Outlet, createRootRoute } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from '#/components/toast-provider'
import { CommandPalette } from '#/components/command-palette'
import { useRealtimeEvents } from '#/hooks/use-realtime-events'
import '../styles.css'

const STORAGE_KEY = 'amanuo_api_key'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RealtimeConnector />
        <CommandPalette />
        <Outlet />
      </ToastProvider>
    </QueryClientProvider>
  )
}

/** Connects WebSocket for real-time cache invalidation. Rendered inside QueryClientProvider. */
function RealtimeConnector() {
  const apiKey = localStorage.getItem(STORAGE_KEY) ?? undefined
  useRealtimeEvents(apiKey)
  return null
}
