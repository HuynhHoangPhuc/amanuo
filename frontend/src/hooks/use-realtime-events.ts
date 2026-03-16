/**
 * Hook: connect WebSocket and invalidate TanStack Query caches on events.
 * Call once at app root (e.g., in __root.tsx layout component).
 */
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { wsClient } from '../lib/websocket-client'

export function useRealtimeEvents(apiKey: string | undefined): void {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!apiKey) return

    wsClient.connect(apiKey)

    const onJobStatus = (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      const d = data as Record<string, unknown> | null
      if (d?.job_id) {
        void queryClient.invalidateQueries({ queryKey: ['jobs', d.job_id] })
      }
    }

    const onBatchProgress = (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
      const d = data as Record<string, unknown> | null
      if (d?.batch_id) {
        void queryClient.invalidateQueries({ queryKey: ['batches', d.batch_id] })
      }
    }

    wsClient.on('job.status', onJobStatus)
    wsClient.on('batch.progress', onBatchProgress)

    return () => {
      wsClient.off('job.status', onJobStatus)
      wsClient.off('batch.progress', onBatchProgress)
      wsClient.disconnect()
    }
  }, [apiKey, queryClient])
}
