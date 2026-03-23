/** Batch processing list with progress bars and expandable detail view. */

import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { BatchListResponse, BatchResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { useToast } from '#/components/toast-provider'
import { XCircle, ChevronDown, ChevronRight, Layers } from 'lucide-react'

export const Route = createFileRoute('/batches')({ component: BatchesPage })

function ProgressBar({ total, processed, failed }: { total: number; processed: number; failed: number }) {
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0
  const failPct = total > 0 ? Math.round((failed / total) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[11px] text-muted-foreground tabular-nums">
        <span>{processed}/{total} processed</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden flex">
        <div className="h-full bg-emerald-500 transition-all" style={{ width: `${pct - failPct}%` }} />
        <div className="h-full bg-red-400 transition-all" style={{ width: `${failPct}%` }} />
      </div>
    </div>
  )
}

function BatchRow({ batch }: { batch: BatchResponse }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(false)

  const cancelMutation = useMutation({
    mutationFn: () => api.post(`/batches/${batch.id}/cancel`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.batches.list() })
      toast('Batch cancelled', 'success')
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const isActive = batch.status === 'pending' || batch.status === 'processing'

  return (
    <div className="border-b border-border/50 last:border-0">
      <div
        className="flex items-center gap-4 px-4 py-3 hover:bg-accent/50 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={14} className="text-muted-foreground" /> : <ChevronRight size={14} className="text-muted-foreground" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <span className="font-mono text-[12px] text-foreground">{batch.id.slice(0, 12)}...</span>
            <StatusBadge status={batch.status} />
          </div>
          <ProgressBar
            total={batch.total_files}
            processed={batch.processed_files}
            failed={batch.failed_files}
          />
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[12px] text-muted-foreground tabular-nums">{new Date(batch.created_at).toLocaleString()}</span>
          {isActive && (
            <button
              onClick={(e) => { e.stopPropagation(); cancelMutation.mutate() }}
              className="text-red-400 hover:text-red-600 p-1 cursor-pointer transition-colors"
              title="Cancel batch"
            >
              <XCircle size={14} />
            </button>
          )}
        </div>
      </div>
      {expanded && batch.job_ids && batch.job_ids.length > 0 && (
        <div className="px-12 pb-3">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Job IDs</p>
          <div className="flex flex-wrap gap-1.5">
            {batch.job_ids.map((id) => (
              <Link
                key={id}
                to="/jobs/$jobId"
                params={{ jobId: id }}
                className="font-mono text-[12px] text-primary hover:underline bg-primary/10 px-2 py-0.5 rounded-md no-underline"
              >
                {id.slice(0, 8)}...
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function BatchesPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.batches.list(),
    queryFn: () => api.get<BatchListResponse>('/batches'),
    refetchInterval: 30_000,
  })

  const batches = data?.batches ?? []

  return (
    <PageLayout title="Batches" description="Track multi-file batch extraction jobs">
      <div className="rounded-lg border border-border bg-card">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Batch Jobs</h2>
          <span className="text-[12px] text-muted-foreground tabular-nums">{data?.total ?? 0} total</span>
        </div>
        <div>
          {isLoading && Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-4 py-3 border-b border-border/50">
              <TableRowSkeleton cols={1} />
            </div>
          ))}
          {!isLoading && batches.map((batch) => (
            <BatchRow key={batch.id} batch={batch} />
          ))}
          {!isLoading && batches.length === 0 && (
            <div className="px-4 py-12 text-center text-muted-foreground">
              <div className="flex flex-col items-center gap-2">
                <Layers size={24} className="text-muted-foreground/40" />
                <p className="text-[13px]">No batch jobs yet.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
